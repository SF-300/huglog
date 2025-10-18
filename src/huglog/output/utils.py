import logging
import typing as t

from ..base import RecordAttr, SpanDict


# NOTE: This function should be called from handler and not from filter because ambient context is filter itself
#       and we don't guarantee, in what order filters are applied.
def ensure_spans_denormalized[T: logging.LogRecord](record: T) -> T:
    try:
        spans: t.Sequence[SpanDict] = getattr(record, RecordAttr.RAW_SPANS)
    except AttributeError:
        return record

    setattr(record, RecordAttr.SPANS_IDS, spans_ids := [])
    setattr(record, RecordAttr.SPANS_MSGS, spans_msgs := [])
    setattr(record, RecordAttr.SPANS_MESSAGES, spans_messages := [])

    for span in spans:
        spans_ids.append(span["id"])
        spans_msgs.append(span["msg"])
        spans_messages.append(span["message"])

    return record
