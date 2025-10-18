# huglog

Structured logging with spans and telemetry integration for Python.

## Installation

```bash
pip install huglog
```

### Optional Dependencies

**Output Formatters:**
```bash
pip install huglog[rich]      # Pretty console output with colors
pip install huglog[logfmt]    # Logfmt structured format
pip install huglog[json]      # JSON structured format
```

**Telemetry Integrations:**
```bash
pip install huglog[sentry]    # Sentry error tracking
pip install huglog[otel]      # OpenTelemetry tracing
```

**Convenience Groups:**
```bash
pip install huglog[all-formatters]  # All output formatters
pip install huglog[all]             # Everything
```

## Quick Start

```python
import logging
from huglog import StdLogger

# Create a logger
logger = StdLogger(logging.getLogger(__name__))

# Use structured logging with context
logger.info("User logged in", {"user_id": "123", "ip": "192.168.1.1"})

# Create spans for tracing
with logger.span("process_order", {"order_id": "456"}) as span_logger:
    span_logger.info("Processing payment")
    span_logger.info("Sending confirmation email")
```

## Features

- **Span-based logging**: Create hierarchical logging contexts
- **Protocol-based design**: Clean abstractions with `LoggerLike` and `SpannerLike` protocols
- **Multiple output formats**: Rich console, logfmt, and JSON formatters (all optional)
- **Telemetry integration**: Optional Sentry and OpenTelemetry support
- **Type-safe**: Full type hints with modern Python type system
- **Minimal core**: Only `frozendict` required, everything else is optional
- **Flexible**: Works with stdlib logging and adapts to various backends

## License

MIT
