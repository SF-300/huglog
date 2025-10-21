import contextlib
import inspect
import typing as t

from huglog.base import Level, LoggerLike
from huglog.utils import find_logger_param
from huglog.utils.span import LoggerParameterNotFoundError


def get_logger_from_params[**P](
    func: t.Callable[P, t.Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> LoggerLike | None:
    signature = inspect.signature(func)

    try:
        param = find_logger_param(signature)
    except LoggerParameterNotFoundError:
        return None

    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()

    try:
        return bound.arguments[param.name]
    except KeyError:
        return None


class StreamToLoggerAdapter:
    @classmethod
    @contextlib.contextmanager
    def running(cls, logger: LoggerLike, level: Level = "INFO"):
        self = cls(logger, level)
        try:
            yield self
        finally:
            with contextlib.suppress(StopIteration):
                self._processor_gen.send(None)
                self._processor_gen.close()

    def __init__(self, logger: LoggerLike, level: Level):
        self._logger = logger
        self._level = level
        self._processor_gen = self._process()
        next(self._processor_gen)

    def _process(self) -> t.Generator:
        while True:
            msg = yield
            if msg is None:
                return
            self._write(msg)

    def _write(
        self, message: str, context: t.Mapping[str, t.Any] | None = None
    ) -> None:
        if context is None:
            context = {}
        self._logger.log(
            t.cast(Level, self._level),
            t.cast(t.LiteralString, message),
            context,
        )

    def write(self, message: str) -> None:
        self._processor_gen.send(message)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:  # pylint: disable=no-self-use
        return False
