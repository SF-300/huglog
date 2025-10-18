import logging
import typing as t
from dataclasses import dataclass
from enum import StrEnum

from frozendict import frozendict


class RecordAttr(StrEnum):
    RAW_SPANS = "huglog_spans"
    SPANS_IDS = "huglog_spans_ids"
    SPANS_MSGS = "huglog_spans_msgs"
    SPANS_MESSAGES = "huglog_spans_messages"


type LevelName = t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type Level = LevelName | int
type Msg = t.LiteralString
type ExcInfo = BaseException
type InContext = t.Mapping[str, t.Any]
type NativeLogger = logging.Logger | logging.LoggerAdapter


@dataclass(frozen=True, slots=True)
class Span:
    id: str
    name: str
    context: frozendict[str, t.Any] = frozendict()


class SpanDict(t.TypedDict):
    id: str
    msg: str
    message: str
    context: t.Mapping[str, t.Any]


@t.runtime_checkable
class LoggerLike(t.Protocol):
    def log(
        self,
        level: Level,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: ExcInfo = ...,
        stacklevel: int = ...,
    ) -> None: ...

    def debug(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: Exception = ...,
        stacklevel: int = ...,
    ): ...

    def info(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: Exception = ...,
        stacklevel: int = ...,
    ): ...

    def warn(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: Exception = ...,
        stacklevel: int = ...,
    ): ...

    def error(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: Exception = ...,
        stacklevel: int = ...,
    ): ...

    def critical(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        exc_info: Exception = ...,
        stacklevel: int = ...,
    ): ...

    def span(
        self,
        msg: Msg,
        context: InContext = ...,
        /,
        sid: str = ...,
    ) -> "SpanLoggerLike": ...


@t.runtime_checkable
class SpanLoggerLike(LoggerLike, t.Protocol):
    def __enter__(self) -> t.Self: ...
    def __exit__(self, *args, **kwargs) -> bool | None: ...
    @t.overload
    def __call__[**P, R](
        self,
        f: t.Callable[P, R],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R: ...
    @t.overload
    def __call__[**P, R1, R2, R3](
        self,
        f: t.Callable[P, t.Generator[R1, R2, R3]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> t.Generator[R1, R2, R3]: ...
    @t.overload
    def __call__[**P, R](
        self,
        f: t.Callable[P, t.Coroutine[t.Any, t.Any, R]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> t.Awaitable[R]: ...
