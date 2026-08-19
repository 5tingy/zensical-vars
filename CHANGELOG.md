# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
