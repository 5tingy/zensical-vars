"""Copy the bundled assets into a docs directory.

The stylesheet and script live in the docs directory like any other custom
asset, registered with extra_css and extra_javascript. This copies them there:

    zensical-vars install docs
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from zensical_vars import ASSETS, asset_path

#: Conventional locations, matching the theme's own documentation.
SUBDIRS = {".css": "stylesheets", ".js": "javascripts"}


def install(docs_dir: Path) -> int:
    if not docs_dir.is_dir():
        print(f"No such directory: {docs_dir.resolve()}", file=sys.stderr)
        print("Pass the path to your docs directory, e.g. zensical-vars install docs")
        return 1

    written = []
    for name in ASSETS:
        target = docs_dir / SUBDIRS[Path(name).suffix] / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset_path(name), target)
        written.append(target)
        print(f"Wrote {target}")

    print("\nNow add to your configuration:\n")
    print("  markdown_extensions:")
    print("    - zensical_vars\n")
    print("  extra_css:")
    print(f"    - {SUBDIRS['.css']}/{ASSETS[0]}")
    print("  extra_javascript:")
    print(f"    - {SUBDIRS['.js']}/{ASSETS[1]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zensical-vars",
        description="Utilities for the zensical-vars Markdown extension.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    installer = sub.add_parser("install", help="copy assets into a docs directory")
    installer.add_argument(
        "docs_dir",
        nargs="?",
        default="docs",
        type=Path,
        help="path to the docs directory (default: docs)",
    )

    args = parser.parse_args(argv)
    return install(args.docs_dir)


if __name__ == "__main__":
    raise SystemExit(main())
