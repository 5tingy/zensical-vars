"""Reader-editable variables for Zensical pages."""

from __future__ import annotations

from pathlib import Path

from zensical_vars.extension import ZensicalVarsExtension, makeExtension

__all__ = ["ZensicalVarsExtension", "makeExtension", "asset_path", "ASSETS"]
__version__ = "1.0.0"

#: Filenames of the bundled assets, in the order they should be registered.
ASSETS = ("zensical-vars.css", "zensical-vars.js")


def asset_path(name: str) -> Path:
    """Return the on-disk path of a bundled asset."""
    if name not in ASSETS:
        raise ValueError(f"unknown asset {name!r}; expected one of {ASSETS}")
    return Path(__file__).parent / "assets" / name
