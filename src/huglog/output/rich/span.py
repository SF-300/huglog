import functools
import operator as op
import re
import typing as t
from abc import abstractmethod
from dataclasses import dataclass

from rich.style import Style

from huglog.base import CustomSpanMsgMarker

type Context = t.Mapping[str, t.Any]
type Compress = t.Callable[[int, Context, Format], str]
type Format = t.Callable[[str, Context], str]


_dsl_re = re.compile(r"([<>=^])?(\d+)")


@functools.cache
def _get_align_and_width(format_spec: str) -> tuple[str | None, int | None]:
    match = _dsl_re.match(format_spec)
    if match:
        align = match.group(1)
        width = int(match.group(2))
        return align, width
    return None, None


class SpanName(str):
    def __new__(
        cls,
        template: t.LiteralString,
        context: t.Mapping[str, t.Any],
        compress: Compress,
        formatter: Format,
    ):
        self = super().__new__(cls, template)
        self._context = context  # type: ignore[attr-defined]
        self._compress = compress  # type: ignore[attr-defined]
        self._formatter = formatter  # type: ignore[attr-defined]
        return self

    def __format__(self, format_spec: str) -> str:
        align, width = _get_align_and_width(format_spec)
        assert not align, "Alignment is not supported for SpanName"
        if width:
            compressed = self._compress(width, self._context, self._formatter)  # type: ignore[attr-defined]
            return compressed
        return self._formatter(self, self._context)  # type: ignore[attr-defined]

    def __str__(self) -> str:
        return self._formatter(self, self._context)  # type: ignore[attr-defined]


def _format_formatter(template: str, context: t.Mapping[str, t.Any]) -> str:
    return template.format(**context)


_percent_formatter = op.mod


class SpanNameTemplate(CustomSpanMsgMarker):
    def __new__(cls, template: t.LiteralString):
        return super().__new__(cls, template)

    def __mod__(self, other: t.Mapping[str, t.Any]) -> SpanName:
        return SpanName(t.cast(t.LiteralString, self), other, self._compress, _percent_formatter)

    def format(self, /, *args, **kwargs) -> SpanName:
        assert not args, "Positional arguments are not supported"
        return SpanName(t.cast(t.LiteralString, self), kwargs, self._compress, _format_formatter)

    @abstractmethod
    def _compress(self, width: int, context: Context, formatter: Format) -> str:
        pass


class TrimmingSpanNameTmpl(SpanNameTemplate):
    def __new__(
        cls,
        template: t.LiteralString,
        alt_template: t.LiteralString | None = None,
    ):
        self = super().__new__(cls, template)
        self._alt_template = (  # type: ignore
            alt_template if alt_template is not None else _get_trimmed_tmpl(template)
        )
        return self

    def _compress(self, width: int, context: Context, formatter: Format) -> str:
        formatted = formatter(self._alt_template, context)  # type: ignore
        return _truncate_with_ellipsis(formatted, width, "middle")


@functools.cache
def _get_trimmed_tmpl(tmpl: str) -> str:
    i = tmpl.find("}")
    i += 1
    return tmpl[:i]


@dataclass(frozen=True, slots=True)
class SpanPath:
    span_messages: t.Sequence[str]
    separator: str = ">"
    style: Style = Style()

    # def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
    #     if not self.span_messages:
    #         yield Text("")
    #         return

    #     sep_width = len(f" {self.separator} ")
    #     sep_overhead = sep_width * len(self.span_messages)
    #     total_width = max(options.max_width - sep_overhead, 10)
    #     span_width = total_width // len(self.span_messages)

    #     yield Text(" ".join(self._components_iter(span_width)), style=self.style)

    def _components_iter(self, span_width: int) -> t.Iterator[str]:
        for span_msg in self.span_messages:
            width = min(span_width, len(span_msg))
            yield self.separator + " " + format(span_msg, str(width))

    # def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
    #     if not self.span_messages:
    #         return Measurement(0, 0)

    #     sep_width = len(f" {self.separator} ")
    #     min_width = (sep_width * len(self.span_messages)) + (3 * len(self.span_messages))
    #     max_width = sum(len(msg) + sep_width for msg in self.span_messages)

    #     return Measurement(min_width, min(max_width, options.max_width))

    def __format__(self, format_spec: str) -> str:
        max_width = int(format_spec) if format_spec.isdigit() else None
        if max_width is None:
            return str(self)
        sep_width = len(f" {self.separator} ")
        sep_overhead = sep_width * len(self.span_messages)
        total_width = max(max_width - sep_overhead, 10)
        try:
            span_width = total_width // len(self.span_messages)
        except ZeroDivisionError:
            return ""

        return " ".join(self._components_iter(span_width))


def _truncate_with_ellipsis(text: str, max_width: int, position: t.Literal["start", "middle", "end"] = "end") -> str:
    if len(text) <= max_width:
        return text

    if max_width < 3:
        return text[:max_width]

    if position == "end":
        return text[: max_width - 3] + "..."
    elif position == "start":
        return "..." + text[-(max_width - 3) :]
    elif position == "middle":
        # For middle ellipsis, distribute remaining chars evenly
        # If odd remainder, give extra char to the end
        remaining = max_width - 3
        left_keep = remaining // 2
        right_keep = remaining - left_keep  # Handles odd widths
        return f"{text[:left_keep]}...{text[-right_keep:]}"
    else:
        raise ValueError(f"Invalid position: {position}")
