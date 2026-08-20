# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-29

Migrated CLI post-install guidance to Zensical TOML file format rather than
the legacy mkdocs YAML.

Also added a demo GIF to the README.md & improved some wording.

## [1.0.0] - 2026-08-19

First stable release. The authoring syntax, the configuration options and the
generated markup are now covered by semantic versioning: anything that would
change the HTML a page produces, or the meaning of a `zvars` block, waits for a
major release.

### Added

**Declaring fields.** A fenced `zvars` block declares the inputs for a page and
renders as the panel. It accepts three shapes: a shorthand mapping of names to
defaults, a list of field definitions, or a `fields` key alongside panel
options. Fields take `label`, `default`, `help`, `placeholder`, a `type` from a
fixed allowlist, and `options` to render a dropdown instead of a text box.

**Referencing values.** `<<name>>` is replaced with the field's default at build
time, in prose, inline code, tables, admonitions, tabbed content and fenced code
blocks — including code that has already been syntax-highlighted. A reference in
an HTML attribute renders its default statically. A backslash escapes a literal
reference, and an undeclared one passes through exactly as written with a
one-time build warning, so `std::cout << x >> y` is left alone.

**The panel.** Rendered as a theme admonition, so its card, icon and colour
scheme come from the theme. `type` selects the admonition kind (`example` by
default), `style: card` switches to a flatter chrome, `collapsible` and `open`
emit a `<details>`, and `panel: false` declares fields without rendering
anything. The heading carries an info icon whose tooltip holds the explanatory
text; reset is an icon button that stays disabled until a value has changed.

**Reader experience.** Text fields show their default as placeholder text, so a
reader types over it rather than deleting first, and clearing a field restores
the default — the page can never display a blank value. Values are remembered
across pages in `localStorage`, and the runtime subscribes to the `document$`
observable so it rebinds after instant navigation.

**Configuration.** `start`, `end`, `block`, `title`, `note`, `reset_label`,
`style`, `type`, `collapsible`, `open`, `persist` and `storage_key` can be set
globally and overridden per block. `panel` is per-block only.

**Packaging.** Installs as a Python-Markdown extension under the name
`zensical_vars`. The stylesheet and script ship inside the wheel, and
`zensical-vars install <docs-dir>` copies them into a docs directory for
registration via `extra_css` and `extra_javascript`.

### Notes

The extension emits page content and nothing else — no injected `<style>` or
`<script>`. This matters because Zensical derives page titles by stripping tags
from rendered HTML, so anything else in the body would surface in the `<title>`,
the header and the search index.

Requires Python 3.9 or later and Python-Markdown 3.4 or later. Note that
Zensical itself may require a newer Python-Markdown than this floor.

## [0.1.0] - Unreleased

Initial release.

- Fenced `zvars` blocks declaring input fields, with defaults, labels, help
  text, input types and dropdowns.
- `<<name>>` references substituted anywhere on the page, including inside
  syntax-highlighted code blocks.
- Panel rendered as a theme admonition, with a `card` alternative, an optional
  collapsible variant and a configurable admonition type.
- Values remembered across pages via `localStorage`.
- MkDocs plugin that registers the extension and its assets automatically.
- `zensical-vars install` for copying the assets under Zensical.
