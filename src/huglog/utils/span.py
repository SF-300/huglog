import functools
import inspect
import typing as t
import warnings

from huglog.base import LoggerLike, Span

LOGGER_PARAM_NAME = "logger"
LOGGER_PARAM_TYPE = LoggerLike


class LoggerParameterNotFoundError(Exception):
    pass


def _find_logger_candidates(sig: inspect.Signature) -> t.Iterator[inspect.Parameter]:
    for name, param in sig.parameters.items():
        # Match by name 'logger' or by annotation being a subclass of LoggerLike
        if name == LOGGER_PARAM_NAME or (
            param.annotation != inspect.Parameter.empty
            and isinstance(param.annotation, type)
            # TODO: Unwrap things like t.Annotation
            and issubclass(param.annotation, LOGGER_PARAM_TYPE)
        ):
            yield param


def run_with_logger_substituted[**P, R](
    logger: LoggerLike,
    func: t.Callable[P, R],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
):
    sig = inspect.signature(func)

    try:
        logger_param = find_logger_param(sig)
    except LoggerParameterNotFoundError as e:
        if __debug__:
            raise e
        warnings.warn(str(e))
        return func(*args, **kwargs)

    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    bound.arguments[logger_param.name] = logger
    return func(*bound.args, **bound.kwargs)


def find_logger_param(sig: inspect.Signature) -> inspect.Parameter:
    candidates = list(_find_logger_candidates(sig))

    match candidates:
        case []:
            raise (AssertionError if __debug__ else LoggerParameterNotFoundError)("No logger parameter found")

        case [p]:
            return p

        case _:
            names = [p.name for p in candidates]
            raise (AssertionError if __debug__ else LoggerParameterNotFoundError)(
                f"Multiple logger parameters found: {names}"
            )


def get_span_message(span: Span) -> str:
    try:
        # return span.name % span.context
        return span.name.format(**span.context)
    except (KeyError, TypeError, ValueError, Exception):
        warnings.warn(f"Failed to format span name: {span}")
        return span.name


@t.overload
def spanned[**P, R](
    span_name: str,
) -> t.Callable[[t.Callable[P, R]], t.Callable[P, R]]: ...


@t.overload
def spanned[**P, R](
    span_name: str,
    infer_context: t.Callable[..., t.Mapping[str, t.Any]],
) -> t.Callable[[t.Callable[P, R]], t.Callable[P, R]]: ...


def spanned(span_name, infer_context=lambda *args, **kwargs: {}):  # type: ignore
    """
    Wraps function calls in logging span context with explicit name and optional context inference
    """

    def decorator(func):
        sig = inspect.signature(func)

        try:
            logger_param = find_logger_param(sig)
        except LoggerParameterNotFoundError as e:
            warnings.warn(str(e))
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)

            # Extract logger instance
            logger = bound.arguments.pop(logger_param.name)

            bound.apply_defaults()

            # Get context and wrap in span
            context = infer_context(*args, **kwargs)
            return logger.span(span_name, context)(
                func,
                *bound.args,
                **bound.kwargs,
            )

        return wrapper

    return decorator
