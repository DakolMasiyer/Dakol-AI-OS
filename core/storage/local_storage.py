import os
import json
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .storage_adapter import StorageAdapter

class LocalStorageBackend(StorageAdapter):
    """
    Local filesystem implementation of the StorageAdapter.
    """

    def __init__(self, base_dir: str = ".data/storage"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        self.audit_log_path = os.path.join(self.base_dir, "storage_audit.jsonl")

    def _get_absolute_path(self, logical_path: str) -> str:
        # Prevent directory traversal
        norm_path = os.path.normpath(logical_path)
        if norm_path.startswith("..") or os.path.isabs(norm_path):
            raise ValueError(f"Invalid logical path: {logical_path}")
        return os.path.join(self.base_dir, norm_path)

    def _log_audit_event(self, event_type: str, logical_path: str, details: Dict[str, Any]):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "logical_path": logical_path,
            "details": details
        }
        # Append-only JSON log
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def save_file(self, logical_path: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        abs_path = self._get_absolute_path(logical_path)
        
        if os.path.exists(abs_path):
            self._log_audit_event("save_failed", logical_path, {"reason": "file_exists"})
            raise FileExistsError(f"File already exists at logical path: {logical_path}")

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(abs_path))
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            
            # Write metadata if provided
            if metadata is not None:
                meta_path = abs_path + ".meta.json"
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf)
                    
            os.rename(temp_path, abs_path)
            self._log_audit_event("save_file", logical_path, {"size": len(content), "metadata": metadata})
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            self._log_audit_event("save_failed", logical_path, {"error": str(e)})
            raise e

        return logical_path

    def load_file(self, logical_path: str) -> bytes:
        abs_path = self._get_absolute_path(logical_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"No file found at logical path: {logical_path}")
            
        with open(abs_path, "rb") as f:
            content = f.read()
        return content

    def delete_file(self, logical_path: str) -> bool:
        abs_path = self._get_absolute_path(logical_path)
        if not os.path.exists(abs_path):
            return False
            
        try:
            os.remove(abs_path)
            meta_path = abs_path + ".meta.json"
            if os.path.exists(meta_path):
                os.remove(meta_path)
            self._log_audit_event("delete_file", logical_path, {})
            return True
        except Exception as e:
            self._log_audit_event("delete_failed", logical_path, {"error": str(e)})
            return False

    def generate_storage_path(self, prefix: str, filename: str) -> str:
        # Standardize prefixes like submissions, screenshots, artifacts
        clean_prefix = prefix.strip("/")
        clean_filename = os.path.basename(filename)
        return f"{clean_prefix}/{clean_filename}"

    def file_exists(self, logical_path: str) -> bool:
        abs_path = self._get_absolute_path(logical_path)
        return os.path.exists(abs_path)

    def get_metadata(self, logical_path: str) -> Dict[str, Any]:
        abs_path = self._get_absolute_path(logical_path)
        meta_path = abs_path + ".meta.json"
        if not os.path.exists(meta_path):
            return {}
            
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_absolute_path(self, logical_path: str) -> str:
        """Helper to get the physical path. Use only when bridging with legacy libraries."""
        return self._get_absolute_path(logical_path)
