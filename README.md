# zensical-vars

Let readers put their own values into your examples. Declare a few fields on a page, reference them in code blocks and prose, and every reference updates as the reader types.

![Demo of the plugin, showing a user modifying the SSH username and IP fields in a codeblock and docs text.](./assets/zensical-vars-demo.gif)

_Note: This is an unoffical zensical plugin, and this project was entirely vibe (or slop) coded by Claude._

````markdown
```zvars
- name: host
  label: Server address
  default: 192.168.1.1
- name: user
  label: Username
  default: my-user
```

```bash
ssh <<user>>@<<host>>
```
````

By providing default values, pages render with `ssh my-user@192.168.1.1`. A reader who enters `10.0.4.20` updates the doc content to `ssh my-user@10.0.4.20`. Defaults are substituted when users modify the value time, so the page even reads correctly with JavaScript disabled.

## Install

This plugin has been tested with zensical version 0.0.55.

```bash
pip install zensical-vars
zensical-vars install docs
```

The second command copies the stylesheet and script into your docs directory,
where they sit like any other customization. Then register all three pieces in
`zensical.toml`:

```toml
[project]
extra_css = ["stylesheets/zensical-vars.css"]
extra_javascript = ["javascripts/zensical-vars.js"]

[project.markdown_extensions.zensical_vars]
type = "example"
```

Projects still carrying a YAML config can use the equivalent keys there, since
Zensical reads that format natively:

```yaml
markdown_extensions:
  - zensical_vars

extra_css:
  - stylesheets/zensical-vars.css
extra_javascript:
  - javascripts/zensical-vars.js
```

Keep any other `markdown_extensions` you already have in that list, since naming the key can replace Zensical's defaults. Re-run `zensical-vars install` after upgrading to refresh the assets.

## Declaring fields

Fields are declared per page in a fenced `zvars` block, which renders as the panel of inputs. Put it where you want the panel to appear.

Shorthand, when a name and a default are all you need:

```yaml
host: 192.168.1.1
user: my-user
```

Full form, with panel options under a `fields` key:

```yaml
title: Point these examples at your own server
collapsible: true       # fold the panel away
open: false             # ...and start it collapsed
panel: false            # declare the fields, render no panel
fields:
  - name: host
    default: 192.168.1.1
    help: The machine you are connecting to.
  - name: port
    default: 22
    type: number        # text, number, password, email, url, tel, search
  - name: shell
    default: bash
    options: [bash, zsh, fish]
```

## Referencing values

Write `<<name>>` in fenced code, inline code, tables, admonitions, tabbed content, link targets or plain prose. Escape a literal with a backslash: `\<<host>>`. Declare the same name on several pages and a reader's value follows them across the site.

## Options

| Option | Default | What it does |
| --- | --- | --- |
| `start` / `end` | `<<` / `>>` | Reference delimiters. |
| `block` | `zvars` | Info string of the declaration fence. |
| `title` | `Use your own values` | Panel heading. |
| `note` | see source | Tooltip on the info icon. `""` hides the icon. |
| `reset_label` | `Reset to defaults` | Accessible label of the reset button. |
| `style` | `admonition` | `admonition` uses a theme card; `card` restyles its chrome. |
| `type` | `example` | Admonition type supplying the icon and colour scheme. |
| `collapsible` | `false` | Render the panel as a collapsible `<details>`. |
| `open` | `true` | Whether a collapsible panel starts expanded. |
| `persist` | `true` | Remember values across pages in the browser. |
| `storage_key` | `zensical-vars` | `localStorage` key used for that. |
| `panel` | `true` | **Block only.** `false` declares the fields but renders no panel. |

Every option except `panel` can be set once in your configuration and overridden per block:

```yaml
markdown_extensions:
  - zensical_vars:
      type: tip
      collapsible: true
```

## The panel

The panel is a theme admonition — the same markup an `!!! example` block produces — so its card, beaker icon and colour scheme come from the theme and follow your palette and colour schemes without configuration. Set `type` to any other admonition kind to change the icon and colour, or `style: card` for a flatter variant with a hairline border and a code-toned background.

`collapsible: true` emits a `<details>`, exactly as `??? example` would, with the theme's own collapse control.

Text fields start empty, showing their default as placeholder text, so a reader types straight over it. Clearing a field returns it to the default, meaning the page can never show a blank value.

## How it works

A reference can't simply be replaced with HTML, because by the time a code block reaches the page the highlighter has already split it into `<span>` tokens. So it runs in two stages: a preprocessor swaps each `<<name>>` for an all-letter sentinel that highlighters treat as an ordinary identifier, then a postprocessor swaps sentinels for live spans in the finished HTML — including inside a Pygments string token.

The extension emits page content and nothing else. The stylesheet and script are ordinary assets, loaded once per site and cached, and the script subscribes to the `document$` observable so it rebinds on instant navigation.

## Limitations

- A reference inside an HTML attribute — `[admin](http://<<host>>/)` — renders with its default and doesn't update live. Nothing breaks; the link just stays pointed at the default.
- Fields must be declared on the page that uses them. Use `panel: false` to declare without rendering a panel.
- An undeclared reference is left exactly as written and logged as a build warning, so `std::cout << x >> y` passes through untouched.

## Development

```bash
pip install -e ".[dev]"
pytest
black .        # formatting
ruff check .   # linting
```

The suite tests this extension, not Zensical: every test renders Markdown directly and asserts on the HTML, so no site build is involved and a bug in any downstream renderer cannot turn the build red.

Both tools are pinned in the `dev` extra so local runs match CI exactly. Black owns formatting at its default 88 columns; ruff lints only, configured to the same width so `E501` and the formatter can never disagree.

The suite covers substitution inside every fence implementation, literal passthrough, escaping, panel markup, the asset installer, and a real Zensical build. CI runs it across Python 3.9–3.13 and against each supported Python-Markdown minor version, since the extension depends on processor priorities relative to the fenced-code and raw-HTML stages.

## Licence

MIT.
