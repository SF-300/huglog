import logging
import typing as t

from rich.console import Console, ConsoleRenderable, Group
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text
from rich.theme import Theme

from ..base import Level, RecordAttr
from .utils import ensure_spans_denormalized


class SpanAwareRichHandler(RichHandler):
    LOGGER_NAME_STYLE = Style(color="thistle1")
    OP_PATH_SEPARATOR = ">"
    SPAN_PATH_STYLE = Style(color="light_steel_blue1")

    LEVEL_MAPPING: t.Mapping[Level, tuple[str, Style]] = {
        "DEBUG": ("DEBUG", Style(color="bright_black", bold=True)),
        "INFO": ("INFO", Style(color="blue", bold=True)),
        "WARNING": ("WARN", Style(color="gold1", bold=True)),
        "ERROR": ("ERROR", Style(color="red", bold=True)),
        "CRITICAL": ("FATAL", Style(color="red1", blink=True, bold=True)),
    }

    class LogfmtHighlighter(RegexHighlighter):
        base_style = "logging.logfmt."
        highlights = [
            r'(?P<key>(?:"(?:[^"\\]|\\.)*"|[\w_]+))(?P<equals>=)(?P<value>(?:"(?:[^"\\]|\\.)*"|[^\s]+))'
        ]

    def __init__(self, *args, **kwargs):
        kwargs["console"] = kwargs.get(
            "console",
            Console(
                theme=Theme(
                    {
                        "logging.keyword": "sandy_brown",
                        "logging.logfmt.key": "tan",
                        "logging.logfmt.equals": "grey30",
                        "logging.logfmt.value": "yellow4",
                    }
                )
            ),
        )
        kwargs["highlighter"] = kwargs.get("highlighter", self.LogfmtHighlighter())
        super().__init__(*args, **kwargs)

    def get_level_text(self, record: logging.LogRecord) -> Text:
        level_name = record.levelname.upper()
        try:
            level_name, style = self.LEVEL_MAPPING[t.cast(Level, level_name)]
        except KeyError:
            level_name, style = level_name, Style(color="grey42")

        return Text.styled(level_name.ljust(5), style)

    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        record = ensure_spans_denormalized(record)
        message_renderable = super().render_message(record, message)
        logger_path = Text(f"{self.OP_PATH_SEPARATOR} {record.name}", style=self.LOGGER_NAME_STYLE)
        span_path = Text(
            " ".join(
                f"{self.OP_PATH_SEPARATOR} {r}"
                for r in getattr(record, RecordAttr.SPANS_MESSAGES, [])
            ),
            style=self.SPAN_PATH_STYLE,
        )
        op_path_renderable = Text(" ").join(f for f in [span_path, logger_path] if f)
        message_renderable = Group(op_path_renderable, message_renderable)
        return message_renderable
