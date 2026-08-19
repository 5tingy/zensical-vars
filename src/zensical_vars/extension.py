"""Markdown extension implementing reader-editable variables.

Authors declare input fields in a fenced ``zvars`` block and reference them
anywhere on the page with ``<<name>>``.  The build emits the default value, so
the page reads correctly with JavaScript disabled; at runtime, typing in a
field rewrites every reference live.

Substitution happens in two stages so that it also works *inside* fenced code
blocks:

1. A preprocessor runs before the fenced-code preprocessor and swaps each
   ``<<name>>`` for an all-letter sentinel token.  Syntax highlighters treat
   the sentinel as a single identifier, so it survives tokenisation intact.
2. A postprocessor runs after the raw-HTML stash has been restored and swaps
   each sentinel for a ``<span data-zv-var="...">`` carrying the default.
"""

from __future__ import annotations

import logging
import re
from html import escape
from typing import Any

import yaml
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

log = logging.getLogger("zensical_vars")

#: Priority above the fenced-code preprocessor (25) and below whitespace
#: normalisation (30), so we see the document exactly as the author wrote it.
PREPROCESSOR_PRIORITY = 28

#: Priority below ``raw_html`` (30) and ``amp_substitute`` (20), so we see the
#: final HTML with all stashed blocks — including highlighted code — restored.
POSTPROCESSOR_PRIORITY = 10

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
TAG_SPLIT_RE = re.compile(r"(<[^>]*>)")

INPUT_TYPES = {"text", "number", "password", "email", "url", "tel", "search"}

_SVG = (
    '<svg class="zv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">{}</svg>'
)

ICON_INFO = _SVG.format(
    '<circle cx="12" cy="12" r="9"/><path d="M12 11.5v5"/>'
    '<circle cx="12" cy="7.75" r="1" fill="currentColor" stroke="none"/>'
)
ICON_RESET = _SVG.format('<path d="M3.5 12a8.5 8.5 0 1 0 2.8-6.3"/><path d="M3 4v5h5"/>')


def _sentinel(index: int) -> str:
    """Return an all-letter token for the nth substitution on a page."""
    letters = ""
    remainder = index
    for _ in range(4):
        letters = chr(ord("a") + remainder % 26) + letters
        remainder //= 26
    return f"zvsub{letters}busvz"


def _tolerant_re(sentinel: str) -> re.Pattern[str]:
    """Match a sentinel even if a lexer split it across tags."""
    return re.compile(r"(?:<[^>]*>)*".join(re.escape(c) for c in sentinel))


def _text(value: Any) -> str:
    """Coerce a YAML scalar to the string a reader should see."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


class Field:
    """One declared input field."""

    def __init__(self, spec: dict[str, Any], uid: str) -> None:
        self.name: str = str(spec["name"])
        self.uid = uid
        self.default = _text(spec.get("default", spec.get("value", "")))
        self.label = _text(spec.get("label", self.name))
        self.help = _text(spec.get("help", spec.get("description", "")))
        self.placeholder = _text(spec.get("placeholder", self.default))
        self.options = spec.get("options") or []

        kind = str(spec.get("type", "text")).lower()
        self.type = kind if kind in INPUT_TYPES else "text"


class State:
    """Per-page state shared between the pre- and postprocessor."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.fields: dict[str, Field] = {}
        self.subs: dict[str, str] = {}
        self.literals: dict[str, str] = {}
        self.patterns: dict[str, re.Pattern[str]] = {}
        self.counter = 0
        self.uid = 0
        self.warned: set[str] = set()

    def add_field(self, spec: dict[str, Any]) -> Field | None:
        name = str(spec.get("name", "")).strip()
        if not NAME_RE.match(name):
            log.warning("zensical_vars: skipping field with invalid name %r", name)
            return None
        self.uid += 1
        field = Field({**spec, "name": name}, uid=f"zv-{name}-{self.uid}")
        self.fields[name] = field
        return field

    def _token(self) -> str:
        token = _sentinel(self.counter)
        self.counter += 1
        self.patterns[token] = _tolerant_re(token)
        return token

    def substitute(self, name: str) -> str:
        token = self._token()
        self.subs[token] = name
        return token

    def passthrough(self, literal: str) -> str:
        """Carry text through untouched that Markdown would otherwise mangle."""
        token = self._token()
        self.literals[token] = literal
        return token


class VarsPreprocessor(Preprocessor):
    """Consume ``zvars`` blocks, then tokenise every ``<<name>>`` reference."""

    def __init__(self, md, config: dict[str, Any], state: State) -> None:
        super().__init__(md)
        self.config = config
        self.state = state

        block = re.escape(str(config["block"]))
        self.open_re = re.compile(
            rf"^(?P<indent>[ ]{{0,3}})(?P<fence>`{{3,}}|~{{3,}})[ ]*{block}[ ]*$"
        )
        self.var_re = re.compile(
            r"(?P<esc>\\?)"
            + re.escape(str(config["start"]))
            + r"[ ]*(?P<name>[A-Za-z_][A-Za-z0-9_.-]*)[ ]*"
            + re.escape(str(config["end"]))
        )

    def run(self, lines: list[str]) -> list[str]:
        self.state.reset()  # one conversion, one page
        lines = self._collect_blocks(lines)
        if not self.state.fields:
            return lines
        return [self.var_re.sub(self._tokenise, line) for line in lines]

    # -- declaration blocks ------------------------------------------------

    def _collect_blocks(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        index = 0
        while index < len(lines):
            match = self.open_re.match(lines[index])
            if not match:
                out.append(lines[index])
                index += 1
                continue

            fence = match.group("fence")
            close_re = re.compile(rf"^[ ]{{0,3}}{fence[0]}{{{len(fence)},}}[ ]*$")
            body: list[str] = []
            index += 1
            while index < len(lines) and not close_re.match(lines[index]):
                body.append(lines[index])
                index += 1
            index += 1  # step over the closing fence

            placeholder = self._build_form("\n".join(body))
            if placeholder is not None:
                out.append(placeholder)
                out.append("")
        return out

    def _build_form(self, source: str) -> str | None:
        try:
            data = yaml.safe_load(source) or {}
        except yaml.YAMLError as error:
            log.warning("zensical_vars: could not parse block: %s", error)
            return None

        specs, options = self._read_shapes(data)
        fields = [f for f in (self.state.add_field(s) for s in specs) if f]
        if not fields:
            return None

        # Declare the fields but render nothing. "form" is the original name of
        # this option, still accepted.
        if not options.get("panel", options.get("form", True)):
            return ""

        html = render_form(fields, self.config, options)
        return self.md.htmlStash.store(html)

    @staticmethod
    def _read_shapes(data: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Accept the three block shapes: shorthand, list, or ``fields:`` map."""
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)], {}
        if not isinstance(data, dict):
            log.warning("zensical_vars: block must be a mapping or a list")
            return [], {}
        if "fields" in data:
            fields = data.get("fields") or []
            options = {k: v for k, v in data.items() if k != "fields"}
            if isinstance(fields, dict):
                return [{"name": k, "default": v} for k, v in fields.items()], options
            return [d for d in fields if isinstance(d, dict)], options
        return [{"name": k, "default": v} for k, v in data.items()], {}

    # -- references --------------------------------------------------------

    def _tokenise(self, match: re.Match[str]) -> str:
        name = match.group("name")
        if match.group("esc"):
            return self.state.passthrough(match.group(0)[1:])
        if name not in self.state.fields:
            if name not in self.state.warned:
                self.state.warned.add(name)
                log.warning("zensical_vars: no field declared for %r", name)
            return self.state.passthrough(match.group(0))
        return self.state.substitute(name)


class VarsPostprocessor(Postprocessor):
    """Replace sentinels in the finished HTML with live-updating spans."""

    def __init__(self, md, config: dict[str, Any], state: State) -> None:
        super().__init__(md)
        self.config = config
        self.state = state

    def run(self, text: str) -> str:
        if not self.state.patterns:
            return text

        # References that landed inside an attribute (a link target, say)
        # cannot carry a span, so those get the plain default value.
        parts = TAG_SPLIT_RE.split(text)
        for i, part in enumerate(parts):
            in_tag = part.startswith("<")
            for token in self.state.patterns:
                if token in part:
                    part = part.replace(token, self._replacement(token, in_tag))
            parts[i] = part
        text = "".join(parts)

        # Fallback for the rare lexer that splits a sentinel across tags.
        if "zvs" in text:
            for token, pattern in self.state.patterns.items():
                text = pattern.sub(
                    lambda _m, t=token: self._replacement(t, in_tag=False), text
                )
        return text

    def _replacement(self, token: str, in_tag: bool) -> str:
        if token in self.state.literals:
            return escape(self.state.literals[token], quote=in_tag)
        field = self.state.fields[self.state.subs[token]]
        if in_tag:
            return escape(field.default, quote=True)
        return self._span(field)

    @staticmethod
    def _span(field: Field) -> str:
        return (
            '<span class="zv-var" data-zv-var="{name}" data-zv-default="{default}">'
            "{default}</span>"
        ).format(
            name=escape(field.name, quote=True),
            default=escape(field.default, quote=True),
        )


def render_form(
    fields: list[Field], config: dict[str, Any], options: dict[str, Any]
) -> str:
    """Build the panel of inputs, as an admonition of the theme's own kind.

    The markup is exactly what the theme expects for an admonition, so the
    card, its icon and its colour scheme all come from the theme. Nothing here
    restyles it — the only thing this adds is what goes inside the body.
    """
    title = _text(options.get("title", config["title"]))
    note = _text(options.get("note", config["note"]))
    persist = bool(options.get("persist", config["persist"]))
    kind = _text(options.get("type", config["type"])).strip() or "example"
    style = _text(options.get("style", config["style"])).strip().lower()
    collapsible = bool(options.get("collapsible", config["collapsible"]))
    is_open = bool(options.get("open", config["open"]))
    reset_label = _text(config["reset_label"])

    # The note becomes a tooltip on an info icon beside the title, so the
    # header stays a single line.
    tip = ""
    if note:
        tip = (
            '<span class="zv-tip" tabindex="0" role="note" aria-label="{note}">'
            '{icon}<span class="zv-tip__bubble">{note}</span></span>'
        ).format(note=escape(note, quote=True), icon=ICON_INFO)

    body = '<div class="zv-panel__fields">{}</div>'.format(
        "".join(_render_field(field) for field in fields)
    )
    body += (
        '<div class="zv-panel__foot">'
        '<button class="zv-panel__reset" type="button" data-zv-reset disabled '
        'title="{label}" aria-label="{label}">{icon}</button>'
        "</div>"
    ).format(label=escape(reset_label, quote=True), icon=ICON_RESET)

    attrs = (
        'data-zv-form data-zv-persist="{persist}" data-zv-storage="{storage}"'
    ).format(
        persist="true" if persist else "false",
        storage=escape(str(config["storage_key"]), quote=True),
    )

    # Both styles are the theme's own admonition markup — the card style just
    # carries an extra class that restyles the chrome. Sharing the markup is
    # what keeps its icon identical: the theme draws it either way.
    classes = escape(kind, quote=True) + " zv-panel"
    if style == "card":
        classes += " zv-panel--card"

    if collapsible:
        return (
            f'<details class="{classes}"{" open" if is_open else ""} {attrs}>'
            f"<summary>{escape(title)}{tip}</summary>"
            f"{body}"
            "</details>"
        )

    return (
        f'<div class="admonition {classes}" {attrs}>'
        f'<p class="admonition-title">{escape(title)}{tip}</p>'
        f"{body}"
        "</div>"
    )


def _render_field(field: Field) -> str:
    attrs = (
        f'id="{escape(field.uid, quote=True)}" '
        f'data-zv-input="{escape(field.name, quote=True)}" '
        f'data-zv-default="{escape(field.default, quote=True)}"'
    )
    if field.options:
        control = f'<select class="zv-field__control" {attrs}>{_render_options(field)}</select>'
    else:
        control = (
            f'<input class="zv-field__control" type="{field.type}" {attrs} '
            f'placeholder="{escape(field.placeholder, quote=True)}" '
            'autocomplete="off" autocapitalize="off" spellcheck="false">'
        )

    help_id = f"{field.uid}-help"
    if field.help:
        control = control.replace(
            "class=", f'aria-describedby="{escape(help_id, quote=True)}" class=', 1
        )
        hint = f'<span class="zv-field__help" id="{escape(help_id, quote=True)}">{escape(field.help)}</span>'
    else:
        hint = ""

    return (
        '<div class="zv-field">'
        f'<label class="zv-field__label" for="{escape(field.uid, quote=True)}">'
        f"{escape(field.label)}</label>"
        f"{control}{hint}"
        "</div>"
    )


def _render_options(field: Field) -> str:
    out = []
    for option in field.options:
        if isinstance(option, dict):
            value = _text(option.get("value", ""))
            label = _text(option.get("label", value))
        else:
            value = label = _text(option)
        selected = " selected" if value == field.default else ""
        out.append(
            f'<option value="{escape(value, quote=True)}"{selected}>{escape(label)}</option>'
        )
    return "".join(out)


class ZensicalVarsExtension(Extension):
    """Register the pre- and postprocessor and hold per-page state."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = {
            "start": ["<<", "Opening delimiter for a reference."],
            "end": [">>", "Closing delimiter for a reference."],
            "block": ["zvars", "Info string of the fenced declaration block."],
            "title": ["Use your own values", "Heading shown above the fields."],
            "note": [
                "Edit a field and the examples on this page update as you type.",
                "Explanatory line shown under the heading.",
            ],
            "reset_label": ["Reset to defaults", "Accessible label of the reset button."],
            "style": [
                "admonition",
                "Panel appearance: 'admonition' uses one of the theme's cards, "
                "'card' uses this extension's own panel.",
            ],
            "type": [
                "example",
                "Admonition type supplying the panel's icon and colour scheme.",
            ],
            "collapsible": [False, "Render the panel as a collapsible details element."],
            "open": [True, "Whether a collapsible panel starts expanded."],
            "persist": [True, "Remember values across pages in this browser."],
            "storage_key": ["zensical-vars", "localStorage key used to remember values."],
        }
        super().__init__(**kwargs)
        self.state = State()

    def extendMarkdown(self, md) -> None:  # noqa: N802 - Markdown API
        md.registerExtension(self)
        config = self.getConfigs()
        md.preprocessors.register(
            VarsPreprocessor(md, config, self.state),
            "zensical_vars",
            PREPROCESSOR_PRIORITY,
        )
        md.postprocessors.register(
            VarsPostprocessor(md, config, self.state),
            "zensical_vars",
            POSTPROCESSOR_PRIORITY,
        )

    def reset(self) -> None:
        self.state.reset()


def makeExtension(**kwargs: Any) -> ZensicalVarsExtension:  # noqa: N802 - Markdown API
    return ZensicalVarsExtension(**kwargs)
