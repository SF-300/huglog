import contextlib
import typing as t
import uuid

import sentry_sdk
import sentry_sdk.api
from sentry_sdk.tracing import Span

from huglog.base import LoggerLike
from huglog.core import LoggerWrapper, spanner_contextmanager


# NOTE: Sentry is already integrated with python logging, so there is no need to explicitly send exceptions
#       and breadcrumbs to Sentry - only spans.
class SentryLogger(LoggerWrapper):
    def __init__(self, wrapped: LoggerLike, span: Span | None = None):
        super().__init__(wrapped)
        self._span = sentry_sdk.api.get_current_span() if span is None else span

    @spanner_contextmanager
    def span(self, name, context=None, sid="") -> t.Iterator[t.Self]:
        context = context or {}

        cls = type(self)

        sid = sid or uuid.uuid4().hex
        with contextlib.ExitStack() as defer:
            span = defer.enter_context(
                sentry_sdk.start_span(
                    name=name,
                    op=context.get("op", None),
                    span_id=sid,
                )
            )
            wrapped = defer.enter_context(super().span(name, context, sid))
            yield cls(wrapped, span)
