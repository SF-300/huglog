from huglog.output.utils import ensure_spans_denormalized

__all__ = [
    "ensure_spans_denormalized",
    "SpanAwareRichHandler",
    "SpanAwareLogFmtFormatter",
    "SpanAwareJsonFormatter",
]

try:
    from huglog.output.rich import SpanAwareRichHandler
except ImportError:

    class SpanAwareRichHandler:  # noqa: N802
        def __new__(cls):
            raise ImportError(
                "SpanAwareRichHandler requires the 'rich' package. "
                "Install it with: pip install huglog[rich]"
            )


try:
    from huglog.output.logfmt import SpanAwareLogFmtFormatter
except ImportError:

    class SpanAwareLogFmtFormatter:  # noqa: N802
        def __new__(cls):
            raise ImportError(
                "SpanAwareLogFmtFormatter requires 'logfmter' and 'boltons' packages. "
                "Install them with: pip install huglog[logfmt]"
            )


try:
    from huglog.output.json import SpanAwareJsonFormatter
except ImportError:

    class SpanAwareJsonFormatter:  # noqa: N802
        def __new__(cls):
            raise ImportError(
                "SpanAwareJsonFormatter requires 'pythonjsonlogger' and 'boltons' packages. "
                "Install them with: pip install huglog[json]"
            )
