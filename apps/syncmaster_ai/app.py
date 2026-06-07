from pathlib import Path

from apps.base_app import AppManifest, AppRuntimeAdapter

MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"


class SyncMasterAI:
    def __init__(self):
        self.manifest = AppManifest.from_file(MANIFEST_PATH)
        self.adapter = AppRuntimeAdapter(app_id=self.manifest.app_id)

    def execute(self, task: str) -> str:
        return self.adapter.execute_task(task, capture_metadata=False)
