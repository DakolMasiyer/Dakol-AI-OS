from pathlib import Path
from typing import Any, Type

from apps.base_app import AppManifest


class AppRegistry:
    _apps: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, app_path: Path) -> None:
        manifest_path = app_path / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"No manifest found at {manifest_path}")

        manifest = AppManifest.from_file(manifest_path)
        if manifest.app_id in cls._apps:
            raise ValueError(f"App {manifest.app_id} is already registered.")

        # In a real system, we might dynamically load the module or store the path
        cls._apps[manifest.app_id] = {
            "manifest": manifest,
            "path": app_path,
        }

    @classmethod
    def get_manifest(cls, app_id: str) -> AppManifest:
        if app_id not in cls._apps:
            raise ValueError(f"App {app_id} not registered.")
        return cls._apps[app_id]["manifest"]

    @classmethod
    def reset(cls) -> None:
        cls._apps.clear()
