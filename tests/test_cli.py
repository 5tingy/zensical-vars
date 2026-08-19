"""Tests for the asset installer."""

from __future__ import annotations

import subprocess
import sys

import zensical_vars


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "zensical_vars.cli", *args],
        capture_output=True,
        text=True,
    )


def test_install_writes_both_assets(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    result = run("install", str(docs))
    assert result.returncode == 0, result.stderr
    assert (docs / "stylesheets" / "zensical-vars.css").is_file()
    assert (docs / "javascripts" / "zensical-vars.js").is_file()


def test_installed_assets_match_the_bundled_ones(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    run("install", str(docs))
    for name in zensical_vars.ASSETS:
        subdir = "stylesheets" if name.endswith(".css") else "javascripts"
        assert (docs / subdir / name).read_text() == zensical_vars.asset_path(
            name
        ).read_text().lstrip("\n")


def test_install_is_idempotent(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    assert run("install", str(docs)).returncode == 0
    assert run("install", str(docs)).returncode == 0


def test_install_reports_a_missing_directory(tmp_path):
    result = run("install", str(tmp_path / "nope"))
    assert result.returncode == 1
    assert "No such directory" in result.stderr


def test_install_prints_the_configuration_to_add(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    output = run("install", str(docs)).stdout
    assert "markdown_extensions" in output
    assert "extra_css" in output
    assert "extra_javascript" in output
