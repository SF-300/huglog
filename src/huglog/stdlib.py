import logging
import typing as t

from frozendict import frozendict

from huglog.base import NativeLogger, RecordAttr, Span
from huglog.core import BaseLoggerWrapper, spanner_contextmanager

type InContext = frozendict[str, t.Any]
type InSpans = tuple[Span, ...]


class StdLogger(BaseLoggerWrapper):
    def __init__(
        self,
        logger: NativeLogger,
        context: InContext | None = None,
        spans: InSpans = (),
    ):
        self._wrapped = logger
        self._context = frozendict({} if context is None else context)
        self._spans = tuple(spans)

    def debug(self, *args, **kwargs):
        return self.log(logging.DEBUG, *args, **self._increment_stacklevel(kwargs))

    def info(self, *args, **kwargs):
        return self.log(logging.INFO, *args, **self._increment_stacklevel(kwargs))

    def warn(self, *args, **kwargs):
        return self.log(logging.WARN, *args, **self._increment_stacklevel(kwargs))

    def error(self, *args, **kwargs):
        return self.log(logging.ERROR, *args, **self._increment_stacklevel(kwargs))

    def critical(self, *args, **kwargs):
        return self.log(logging.CRITICAL, *args, **self._increment_stacklevel(kwargs))

    def log(self, level, msg, context=None, **kwargs):
        numeric_level = level
        if not isinstance(numeric_level, int):
            numeric_level = logging.getLevelNamesMapping()[level.upper()]

        # NOTE: This library doesn't make any distinction between "extra" and "context" to make
        #       structured logging a bit more ergonomic.
        args = [numeric_level, msg]
        if context := {**self._context, **(context or {})}:
            args.append(context)

        assert RecordAttr.RAW_SPANS not in context
        extra = {**context, RecordAttr.RAW_SPANS: self._spans}

        return self._wrapped.log(
            *args, extra=extra, **self._increment_stacklevel(kwargs)
        )

    @spanner_contextmanager
    def span(self, msg, context=None, /, sid=""):
        try:
            yield self
        finally:
            pass
