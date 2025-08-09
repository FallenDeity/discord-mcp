from __future__ import annotations

import collections
import typing as t

from discord_mcp.core.server.shared.manifests import BaseManifest, ResourceManifest

__all__: tuple[str, ...] = ("ManifestRepository",)


class ManifestRepository:
    def __init__(self) -> None:
        self._manifests: t.DefaultDict[type[BaseManifest], dict[str, BaseManifest]] = collections.defaultdict(dict)

    def add_manifest(self, manifest: BaseManifest) -> None:
        if not isinstance(manifest, BaseManifest):  # type: ignore
            raise TypeError(f"Expected BaseManifest, got {type(manifest).__name__}")

        manifest_type = type(manifest)
        key = manifest.uri if isinstance(manifest, ResourceManifest) else manifest.name
        if key is None:
            raise ValueError("Manifest must have a name or URI")
        self._manifests[manifest_type][key] = manifest

    def get_manifest(self, manifest_type: type[BaseManifest], key: str) -> BaseManifest | None:
        return self._manifests.get(manifest_type, {}).get(key)

    def add_manifests(self, manifests: t.Iterable[BaseManifest]) -> None:
        for manifest in manifests:
            self.add_manifest(manifest)
