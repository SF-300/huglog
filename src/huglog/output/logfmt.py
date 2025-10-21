import logging
import typing as t
from datetime import datetime

from logfmter import Logfmter
from logfmter.formatter import RESERVED

from huglog.base import RecordAttr
from huglog.output.utils import ensure_spans_denormalized


class SpanAwareLogFmtFormatter(Logfmter):
    def __init__(
        self,
        include_keys: list[str],
        exclude_keys: t.Sequence[str] = tuple(),
        datefmt: str = "%H:%M:%S:%f",
    ):
        # HACK: For some weird reason, LogfmtFormatter doesn't call super().__init__ in its own __init__
        #       so we need to call it manually. Otherwise, something somewhere breaks due to missing
        #       attributes in certain conditions.
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._exclude_keys = exclude_keys
        Logfmter.__init__(self, keys=include_keys, datefmt=datefmt)

    # HACK: Copied from Logfmter to add custom exclude keys support
    def get_extra(self, record: logging.LogRecord) -> dict:
        extras = {}

        for key, value in record.__dict__.items():
            key = self.normalize_key(key)

            if key in RESERVED:
                continue
            if key in self._exclude_keys:
                continue

            if isinstance(value, dict):
                extras.update(self.flatten_dict(value, key))
            else:
                extras[key] = value

        return extras

    def formatTime(self, record, datefmt=None):  # noqa: N802
        if not datefmt:
            return super().formatTime(record, datefmt=datefmt)
        return datetime.fromtimestamp(record.created).astimezone().strftime(datefmt)

    def format(self, record: logging.LogRecord) -> str:
        record = ensure_spans_denormalized(record)
        return super().format(record)


class SpanAwareStdoutLogFmtFormatter(SpanAwareLogFmtFormatter):
    def __init__(
        self,
        include_keys: list[str] = ("msg",),
        exclude_keys: t.Sequence[str] = tuple(),
        datefmt: str = "%H:%M:%S:%f",
    ):
        exclude_keys = (*exclude_keys, *RecordAttr, "at")
        super().__init__(
            include_keys=include_keys,
            exclude_keys=exclude_keys,
            datefmt=datefmt,
        )
