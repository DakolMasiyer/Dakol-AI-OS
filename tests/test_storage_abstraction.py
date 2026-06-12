import os
import json
import pytest
import shutil
import time
from typing import Dict, Any

from core.storage.storage_adapter import StorageAdapter
from core.storage.local_storage import LocalStorageBackend

@pytest.fixture
def storage():
    # Use a specific test directory
    test_dir = ".data/test_storage_" + str(int(time.time()))
    backend = LocalStorageBackend(base_dir=test_dir)
    yield backend
    # Cleanup after test
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def test_adapter_portability(storage):
    assert isinstance(storage, StorageAdapter)

def test_path_generation_stability(storage):
    path1 = storage.generate_storage_path("submissions/", "/path/to/my_file.pdf")
    assert path1 == "submissions/my_file.pdf"
    
    path2 = storage.generate_storage_path("/screenshots", "shot.png")
    assert path2 == "screenshots/shot.png"

def test_basic_save_and_load(storage):
    logical_path = storage.generate_storage_path("artifacts", "test1.txt")
    content = b"hello world"
    metadata = {"mime_type": "text/plain", "author": "test"}
    
    saved_path = storage.save_file(logical_path, content, metadata=metadata)
    assert saved_path == logical_path
    
    assert storage.file_exists(logical_path)
    loaded_content = storage.load_file(logical_path)
    assert loaded_content == content
    
    loaded_metadata = storage.get_metadata(logical_path)
    assert loaded_metadata == metadata

def test_duplicate_upload_handling(storage):
    logical_path = storage.generate_storage_path("artifacts", "duplicate.txt")
    storage.save_file(logical_path, b"content1")
    
    with pytest.raises(FileExistsError):
        storage.save_file(logical_path, b"content2")
        
    # Content should remain unchanged
    assert storage.load_file(logical_path) == b"content1"

def test_atomic_write_simulation(storage, monkeypatch):
    logical_path = storage.generate_storage_path("artifacts", "atomic.txt")
    
    # Simulate a crash during save_file by mocking os.rename
    original_rename = os.rename
    def crashing_rename(src, dst):
        raise RuntimeError("Simulated crash during atomic write")
    
    monkeypatch.setattr(os, "rename", crashing_rename)
    
    with pytest.raises(RuntimeError, match="Simulated crash"):
        storage.save_file(logical_path, b"partial content")
        
    # Check that file does not exist (the atomic temp file should be cleaned up by the except block)
    assert not storage.file_exists(logical_path)

def test_delete_file(storage):
    logical_path = storage.generate_storage_path("artifacts", "delete.txt")
    storage.save_file(logical_path, b"content", metadata={"key": "val"})
    
    assert storage.file_exists(logical_path)
    assert storage.delete_file(logical_path) is True
    
    assert not storage.file_exists(logical_path)
    assert storage.get_metadata(logical_path) == {}
    
    # Deleting non-existent file
    assert storage.delete_file(logical_path) is False

def test_audit_logging(storage):
    logical_path = storage.generate_storage_path("artifacts", "audit.txt")
    storage.save_file(logical_path, b"test", metadata={"foo": "bar"})
    storage.delete_file(logical_path)
    
    # Check the audit log
    audit_path = storage.audit_log_path
    assert os.path.exists(audit_path)
    
    events = []
    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line.strip()))
            
    assert len(events) >= 2
    assert events[0]["event"] == "save_file"
    assert events[0]["logical_path"] == logical_path
    assert events[0]["details"]["size"] == 4
    
    assert events[1]["event"] == "delete_file"
    assert events[1]["logical_path"] == logical_path
