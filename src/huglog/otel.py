import contextlib
import logging
import typing as t
import uuid
from datetime import timedelta

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from .core import LoggerWrapper, spanner_contextmanager


class OtelLoggingHandler(LoggingHandler):
    @classmethod
    @contextlib.contextmanager
    def running(
        cls,
        *,
        service_name: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        level: int = logging.NOTSET,
        exporter_timeout: timedelta = timedelta(seconds=10),
        max_queue_size: int = 2048,
        schedule_delay: timedelta = timedelta(seconds=5),
        export_batch_size: int = 512,
    ) -> t.Iterator[t.Self]:
        resource = Resource.create({SERVICE_NAME: service_name})

        provider = LoggerProvider(resource=resource)
        set_logger_provider(provider)

        exporter = OTLPLogExporter(
            endpoint=endpoint,
            headers=headers,
            timeout=exporter_timeout.total_seconds(),
        )

        processor = BatchLogRecordProcessor(
            exporter,
            max_queue_size=max_queue_size,
            schedule_delay_millis=schedule_delay.total_seconds() * 1000,
            export_timeout_millis=exporter_timeout.total_seconds() * 1000,
            max_export_batch_size=export_batch_size,
        )
        provider.add_log_record_processor(processor)

        handler = cls(level=level, logger_provider=provider)

        with contextlib.ExitStack() as defer:
            defer.callback(provider.shutdown)
            defer.callback(provider.force_flush)
            yield handler


class OtelLogger(LoggerWrapper):
    @spanner_contextmanager
    def span(
        self,
        name: str,
        context: t.Mapping[str, t.Any] | None = None,
        sid: str = "",
    ) -> t.Iterator["OtelLogger"]:
        cls = type(self)
        context = context or {}
        sid = sid or uuid.uuid4().hex

        tracer = trace.get_tracer(__name__)

        with contextlib.ExitStack() as defer:
            # Start OTEL span
            defer.enter_context(tracer.start_as_current_span(name, attributes=dict(context)))
            # Start underlying logging span
            wrapped = defer.enter_context(super().span(name, context, sid))
            # Yield new logger wrapping both
            yield cls(wrapped)
