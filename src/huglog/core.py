import asyncio as aio
import contextlib
import inspect
import logging
import typing as t
import unittest.mock

from huglog.base import LoggerLike, SpanLoggerLike
from huglog.utils import run_with_logger_substituted


class BaseLoggerWrapper(LoggerLike, t.Protocol):
    _wrapped: t.Any

    def log(self, *args, **kwargs) -> None:
        return self._wrapped.log(*args, **self._increment_stacklevel(kwargs))

    def debug(self, *args, **kwargs):
        return self._wrapped.debug(*args, **self._increment_stacklevel(kwargs))

    def info(self, *args, **kwargs):
        return self._wrapped.info(*args, **self._increment_stacklevel(kwargs))

    def warn(self, *args, **kwargs):
        return self._wrapped.warn(*args, **self._increment_stacklevel(kwargs))

    def error(self, *args, **kwargs):
        return self._wrapped.error(*args, **self._increment_stacklevel(kwargs))

    def critical(self, *args, **kwargs):
        return self._wrapped.critical(*args, **self._increment_stacklevel(kwargs))

    def span(self, *args, **kwargs) -> SpanLoggerLike:
        return self._wrapped.span(*args, **kwargs)

    def _increment_stacklevel[T: t.MutableMapping](self, kwargs: T) -> T:
        stacklevel = kwargs.get("stacklevel", 1)
        assert isinstance(stacklevel, int)
        kwargs["stacklevel"] = stacklevel + 1
        return kwargs

    def __str__(self) -> str:
        return str(self._wrapped)


class LoggerWrapper(BaseLoggerWrapper):
    def __init__(self, wrapped: LoggerLike) -> None:
        self.__wrapped = wrapped

    @property
    def _wrapped(self) -> LoggerLike:
        return self.__wrapped


class SpanLogger(BaseLoggerWrapper, SpanLoggerLike):
    def __init__(self, cm: t.ContextManager[LoggerLike]) -> None:
        self._cm = cm
        self._logger: LoggerLike | None = None

    @property
    def _wrapped(self) -> LoggerLike:
        if self._logger is None:
            raise RuntimeError(
                "SpanLogger is not active. Use it as a context manager: with logger.span(...) as span: ..."
            )
        return self._logger

    def __enter__(self):
        result = self._cm.__enter__()
        assert not isinstance(result, SpanLoggerLike)
        self._logger = result
        return self

    def __exit__(self, *args, **kwargs):
        result = self._cm.__exit__(*args, **kwargs)
        self._logger = None
        return result

    def __call__(self, f: t.Callable[..., t.Any], /, *args: t.Any, **kwargs: t.Any) -> t.Any:
        if inspect.isgeneratorfunction(f):

            def gen_driver():
                with self._cm as logger:
                    yield from run_with_logger_substituted(logger, f, *args, **kwargs)

            return gen_driver()

        if not aio.iscoroutinefunction(f):
            with self._cm as logger:
                return run_with_logger_substituted(logger, f, *args, **kwargs)

        async def coro_driver():
            # NOTE: As a precaution against stuff like "Eager Task Factory", yield control to event loop to ensure that
            #       we've been scheduled at least once, so that we run actual interesting code inside the
            #       already-copied contextvars.Context (if copying will take place at all).
            await aio.sleep(0)
            with self._cm as logger:
                return await run_with_logger_substituted(logger, f, *args, **kwargs)

        return coro_driver()


def spanner_contextmanager[**PO](
    func: t.Callable[PO, t.Iterator[LoggerLike]],
) -> t.Callable[PO, SpanLoggerLike]:
    cm_func = contextlib.contextmanager(func)
    return lambda *args, **kwargs: SpanLogger(cm_func(*args, **kwargs))


class _NullLogger(LoggerWrapper):
    def __init__(self) -> None:
        super().__init__(unittest.mock.Mock(spec=logging.Logger))

    @spanner_contextmanager
    def span(self, *args, **kwargs):
        yield self

    def __bool__(self):
        return False


null_logger = _NullLogger()
