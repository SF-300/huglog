import functools
import logging
import re

from huglog.utils.span import (
    LoggerParameterNotFoundError,
    find_logger_param,
    get_span_message,
    run_with_logger_substituted,
    spanned,
)

__all__ = (
    "LoggerParameterNotFoundError",
    "extract_placeholders",
    "NormalizingFilter",
    "run_with_logger_substituted",
    "get_span_message",
    "spanned",
    "find_logger_param",
)


_pattern = r"%\((.*?)\)[diouxXeEfFgGcrs%]"


@functools.cache
def extract_placeholders(format_string: str) -> tuple[str]:
    """
    Extract all placeholders in the format %(name)s from a string.

    Args:
        format_string: The string containing %-style placeholders

    Returns:
        List of placeholder names without the %(...)x wrapper
    """
    return tuple(re.findall(_pattern, format_string))


class NormalizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # NOTE: Unicorn sometimes logs exceptions as messages
        if isinstance(record.msg, BaseException):
            exc = record.msg
            record.msg = str(exc)
            record.exc_text = str(exc)
            record.exc_info = (type(exc), exc, exc.__traceback__)
        return True
