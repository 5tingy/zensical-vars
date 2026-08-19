"""MkDocs plugin wiring, for projects still built with MkDocs.

Zensical does not load third-party MkDocs plugins — it maps a known set of
plugins onto its own modules — so under Zensical the assets are copied into the
docs directory instead, with ``zensical-vars install``. This plugin exists so
that MkDocs users get the usual one-line setup, with no assets to place:

    plugins:
      - zensical-vars
"""

from __future__ import annotations

from typing import Any

from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files

from zensical_vars import ASSETS, asset_path

#: Where the assets are published within the built site.
DEST_DIR = "assets/zensical-vars"


class ZensicalVarsPlugin(BasePlugin):
    """Register the Markdown extension and serve its assets."""

    def on_config(self, config: Any) -> Any:
        extensions = config.get("markdown_extensions") or []
        if "zensical_vars" not in extensions:
            extensions.append("zensical_vars")
            config["markdown_extensions"] = extensions

        for name in ASSETS:
            uri = f"{DEST_DIR}/{name}"
            key = "extra_css" if name.endswith(".css") else "extra_javascript"
            listing = config.get(key) or []
            if uri not in listing:
                listing.append(uri)
                config[key] = listing
        return config

    def on_files(self, files: Files, config: Any) -> Files:
        for name in ASSETS:
            files.append(self._file(f"{DEST_DIR}/{name}", asset_path(name), config))
        return files

    @staticmethod
    def _file(uri: str, source: Any, config: Any) -> File:
        generated = getattr(File, "generated", None)
        if generated is not None:  # MkDocs >= 1.6
            return generated(config, uri, abs_src_path=str(source))
        handle = File(
            source.name,
            str(source.parent),
            config["site_dir"],
            config["use_directory_urls"],
        )
        handle.dest_uri = uri
        handle.abs_dest_path = f"{config['site_dir']}/{uri}"
        handle.url = uri
        return handle
