import contextvars
import logging
import sys
import typing as t
from collections import ChainMap
from contextvars import ContextVar
from copy import copy
from uuid import uuid4
from weakref import WeakKeyDictionary

from frozendict import frozendict

from .base import NativeLogger, RecordAttr, Span, SpanDict
from .core import spanner_contextmanager
from .stdlib import StdLogger
from .utils import extract_placeholders, get_span_message


class _MergedSpans(t.NamedTuple):
    context: t.Mapping[str, t.Any]
    spans: t.Sequence[Span]


# TODO: Add safeguards against having more then on AmbientContextLogger in the same context?
class AmbientContextHolder(logging.Filter):
    class State(t.TypedDict):
        reserved_depth: int
        spans: t.Sequence[Span]

    _cvars: tuple[ContextVar[Span | None], ...]

    def __new__(cls, *args, **kwargs):
        if cls is AmbientContextHolder:
            raise TypeError("AmbientContextHolder must be subclassed and cannot be instantiated directly")
        return super().__new__(cls)

    def __init_subclass__(cls) -> None:
        # HACK: contextvars API is rather limited and provides no way (at Python level) to influence, how entries in
        #       HAMT mapping are copied themselves. The only thing we actually can rely upon is the shallow copying of
        #       the mapping itself by the runtime. This means, that we have to emulate the dictionary-like API on top
        #       of individual contextvars to actually be able to refer to all the previous spans in the stack, while
        #       references to them are automatically copied, when contextvars.Context is copied, so that we get a
        #       distinct copy of our "spans stack" inside of each contextvars.Context.
        cls._cvars = tuple(
            ContextVar(f"ambient ctx depth {i}")
            for i in range(
                sys.getrecursionlimit(),
            )
        )
        return super().__init_subclass__()

    def __init__(self, reserved_depth: int = 0) -> None:
        if reserved_depth < 0:
            raise ValueError("reserved_depth must be non-negative")
        super().__init__()
        self._reserved_depth = reserved_depth
        # NOTE: Minor optimization for cases when this same filter is attached to multiple loggers/handlers
        self._processed = WeakKeyDictionary()

    @property
    def reserved_depth(self) -> int:
        return self._reserved_depth

    def set_span(self, depth: int, span: Span) -> contextvars.Token:
        assert len(self._cvars) > depth >= 0
        cvar = self._cvars[depth]

        if __debug__:
            try:
                cvar.get(cvar.get())
            except LookupError:
                pass
            else:
                raise AssertionError(
                    f"Context variable for {depth} already has some value set. "
                    "Ensure that you are actually using the logger returned from `.span()` method and not the "
                    "original one to log messages that belong to the span and to spawn new child spans."
                )

        return cvar.set(span)

    def del_span(self, depth: int, token: contextvars.Token) -> None:
        assert len(self._cvars) > depth >= 0

        cvar = self._cvars[depth]
        cvar.reset(token)

    def _enrich_record(self, record: logging.LogRecord, context: t.Mapping[str, t.Any]) -> logging.LogRecord:
        record = copy(record)

        if context and not record.args:
            record.args = dict()

        if isinstance(record.args, dict):
            # NOTE: context is a merged view of all span contexts, so let's try to expand args of this
            #       record with everything requested in it from anywhere in the span stack
            placeholders = extract_placeholders(record.msg)
            for key in placeholders:
                if key in record.args:
                    continue
                try:
                    t.cast(dict, record.args)[key] = context[key]
                except KeyError:
                    continue

        # for key, value in context.items():
        #     if hasattr(record, key):
        #         continue
        #     setattr(record, key, value)

        return record

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        if record not in self._processed:
            # NOTE: All merging have to happen here (and not when logger emits) because this filter can be actually fed
            #       by stdlib loggers without our wrappers, that happen to be called inside the stack in which .span is
            #       active somewhere above them.
            context, spans = self._get_merged_spans()

            # assert not hasattr(record, RecordAttr.RAW_SPANS)
            new_record = self._enrich_record(record, context)

            setattr(
                new_record,
                RecordAttr.RAW_SPANS,
                (
                    *getattr(
                        record,
                        RecordAttr.RAW_SPANS,
                        tuple(),
                    ),
                    *(
                        SpanDict(
                            id=s.id,
                            msg=s.name,
                            message=get_span_message(s),
                            context=s.context,
                        )
                        for s in spans
                    ),
                ),
            )

            self._processed[record] = new_record

        return self._processed[record]

    def _spans_iter(self, target_depth: int | None = None):
        if target_depth is None:
            target_depth = len(self._cvars)
        for depth in range(self._reserved_depth, target_depth):
            cvar = self._cvars[depth]
            try:
                current_value = cvar.get()
            except LookupError:
                break
            if current_value is None:
                continue
            assert isinstance(current_value, Span)
            yield current_value

    def _get_merged_spans(self, target_depth: int | None = None) -> _MergedSpans:
        spans, contexts = [], []
        for span in self._spans_iter(target_depth):
            spans.append(span)
            contexts.append(span.context)

        return _MergedSpans(
            context=ChainMap(*contexts),
            spans=spans,
        )

    def __getstate__(self):
        return AmbientContextHolder.State(
            reserved_depth=self._reserved_depth,
            spans=tuple(self._spans_iter()),
        )

    def __setstate__(self, state):
        reserved_depth = state["reserved_depth"]
        self.__init__(reserved_depth=reserved_depth)
        spans = state["spans"]
        for depth, span in enumerate(spans):
            self.set_span(reserved_depth + depth, span)


class AmbientContextLogger(StdLogger):
    class State(t.TypedDict):
        logger_name: str
        context_holder_state: AmbientContextHolder.State
        # own_depth: int

    @classmethod
    def from_state(
        cls,
        state: State,
        context_holder_type: type[AmbientContextHolder],
    ) -> t.Self:
        own_depth = state["context_holder_state"]["reserved_depth"] + len(state["context_holder_state"]["spans"])
        holder = context_holder_type.__new__(context_holder_type)
        holder.__setstate__(state["context_holder_state"])
        logger = logging.getLogger(state["logger_name"])
        return cls(logger, holder, own_depth)

    # @classmethod
    # def from_raw_logger(
    #     cls,
    #     logger: logging.Logger,
    #     context_holder: AmbientContextHolder,
    # ) -> t.Self:
    #     logger.addFilter(context_holder)
    #     own_depth = context_holder.reserved_depth
    #     self = cls(logger, context_holder, own_depth)
    #     return self

    # @property
    # def depth(self) -> int:
    #     return self._own_depth

    def __init__(
        self,
        logger: NativeLogger,
        context_holder: AmbientContextHolder,
        own_depth: int | None = None,
    ) -> None:
        if own_depth is None:
            own_depth = context_holder.reserved_depth
        if own_depth < context_holder.reserved_depth:
            raise ValueError("own_depth must be greater or equal to context_holder.reserved_depth")
        super().__init__(logger)
        self._context_holder = context_holder
        self._own_depth = own_depth

    @property
    def context_holder(self) -> AmbientContextHolder:
        return self._context_holder

    @spanner_contextmanager
    def span(self, name, context=None, /, sid="") -> t.Iterator[t.Self]:
        cls = type(self)

        if context is None:
            context = {}
        sid = sid or uuid4().hex

        assert isinstance(context, t.Mapping)

        if __debug__ and isinstance(context, t.Mapping) and any(a in context for a in RecordAttr):
            raise AssertionError("Context can not contain reserved keys: " + ", ".join(RecordAttr))

        span = Span(
            id=sid,
            name=name,
            context=frozendict(context),
        )

        reset_token = self._context_holder.set_span(self._own_depth, span)
        try:
            yield cls(self._wrapped, self._context_holder, self._own_depth + 1)
        finally:
            # NOTE: If GeneratorExit is raised, we assume that it's due to the garbage collection of the generator
            #       (as this generator func is not accessible per ser but only through the contextmanager wrapper),
            #       and the context is guaranteed to not be the same anymore and will fail.
            if not isinstance(sys.exc_info()[1], GeneratorExit):
                self._context_holder.del_span(self._own_depth, reset_token)

    def __getstate__(self) -> State:
        return {
            "logger_name": self._wrapped.name,
            "context_holder_state": self._context_holder.__getstate__(),
            # "own_depth": self._own_depth,
        }
