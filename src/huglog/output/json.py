import logging

from boltons.tbutils import ExceptionInfo
from pythonjsonlogger.json import JsonFormatter

from huglog.output.utils import ensure_spans_denormalized


class SpanAwareJsonFormatter(JsonFormatter):
    def formatException(self, ei):  # noqa: N802
        exc_info = ExceptionInfo.from_exc_info(*ei)
        return exc_info.to_dict()

    def formatStack(self, stack_info):  # noqa: N802
        # TODO: Implement stack_info serialization
        return super().formatStack(stack_info)

    def format(self, record: logging.LogRecord) -> str:
        record = ensure_spans_denormalized(record)
        return super().format(record)
