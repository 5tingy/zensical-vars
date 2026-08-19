"""End-to-end tests: a real MkDocs build, and the asset installer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

mkdocs = pytest.importorskip("mkdocs")

PAGE = """\
# SSH example

```zvars
- name: host
  label: Server address
  default: 192.168.1.1
```

```bash
ssh me@<<host>>
```
"""

CONFIG = """\
site_name: Test
plugins:
  - zensical-vars
markdown_extensions:
  - fenced_code
  - codehilite
"""


def build_site(tmp_path: Path, config: str = CONFIG) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text(PAGE)
    (tmp_path / "mkdocs.yml").write_text(config)
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return tmp_path / "site"


def test_plugin_copies_assets_into_the_site(tmp_path):
    site = build_site(tmp_path)
    assert (site / "assets" / "zensical-vars" / "zensical-vars.css").is_file()
    assert (site / "assets" / "zensical-vars" / "zensical-vars.js").is_file()


def test_plugin_registers_assets_in_the_page_head(tmp_path):
    html = (build_site(tmp_path) / "index.html").read_text()
    assert 'href="assets/zensical-vars/zensical-vars.css"' in html
    assert 'src="assets/zensical-vars/zensical-vars.js"' in html


def test_plugin_registers_the_markdown_extension(tmp_path):
    """The plugin alone should be enough; no markdown_extensions entry needed."""
    html = (build_site(tmp_path) / "index.html").read_text()
    assert 'data-zv-var="host"' in html


def test_built_page_title_is_not_polluted(tmp_path):
    """A <style> or <script> in the body leaks into the title and the nav."""
    html = (build_site(tmp_path) / "index.html").read_text()
    title = html[html.index("<title>") : html.index("</title>")]
    assert "zv-panel" not in title
    assert len(title) < 120


def test_default_is_substituted_inside_the_code_block(tmp_path):
    html = (build_site(tmp_path) / "index.html").read_text()
    highlighted = html[html.index("<pre") : html.index("</pre>")]
    assert "192.168.1.1" in highlighted


def test_cli_installs_assets(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "zensical_vars.cli", "install", str(docs)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (docs / "stylesheets" / "zensical-vars.css").is_file()
    assert (docs / "javascripts" / "zensical-vars.js").is_file()


def test_cli_reports_a_missing_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "zensical_vars.cli", "install", str(tmp_path / "nope")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No such directory" in result.stderr
