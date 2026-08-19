"""End-to-end tests: a real Zensical build.

Skipped when Zensical isn't installed, so the suite still runs without the
optional dependency.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
[project]
site_name = "Test"
extra_css = ["stylesheets/zensical-vars.css"]
extra_javascript = ["javascripts/zensical-vars.js"]
markdown_extensions = [
  "pymdownx.superfences",
  "pymdownx.highlight",
  "zensical_vars",
]
"""

if os.environ.get("ZENSICAL_VARS_REQUIRE_BUILD"):
    # CI sets this so a missing dependency fails loudly instead of quietly
    # skipping the only tests that exercise a real build.
    import zensical  # noqa: F401
else:
    pytest.importorskip("zensical", reason="zensical is not installed")


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    """Build a one-page site the way a reader's project would."""
    root = tmp_path_factory.mktemp("project")
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text(PAGE)
    (root / "zensical.toml").write_text(CONFIG)

    installed = subprocess.run(
        [sys.executable, "-m", "zensical_vars.cli", "install", str(root / "docs")],
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, installed.stderr

    build = subprocess.run(
        [shutil.which("zensical") or "zensical", "build"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr + build.stdout
    return root / "site"


def test_assets_are_published(site):
    assert (site / "stylesheets" / "zensical-vars.css").is_file()
    assert (site / "javascripts" / "zensical-vars.js").is_file()


def test_assets_are_linked_from_the_page(site):
    html = (site / "index.html").read_text()
    assert "zensical-vars.css" in html
    assert "zensical-vars.js" in html


def test_default_is_substituted_inside_the_code_block(site):
    html = (site / "index.html").read_text()
    highlighted = html[html.index("<pre") : html.index("</pre>")]
    assert "192.168.1.1" in highlighted
    assert 'data-zv-var="host"' in highlighted


def test_panel_is_rendered(site):
    html = (site / "index.html").read_text()
    assert "admonition example zv-panel" in html


def test_page_title_is_not_polluted(site):
    """A <style> or <script> in the body leaks into the title and the header."""
    html = (site / "index.html").read_text()
    title = html[html.index("<title>") : html.index("</title>")]
    assert "zv-panel" not in title
    assert len(title) < 120


def test_nothing_is_inlined_into_the_page_body(site):
    """Anything inlined here also reaches the title and the search index."""
    html = (site / "index.html").read_text()
    assert ".zv-panel__fields" not in html
    assert "DEFAULT_STORAGE_KEY" not in html
