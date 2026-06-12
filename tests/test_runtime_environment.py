from __future__ import annotations

import pytest

from runtime import environment


def test_runtime_manifest_includes_dependency_versions(monkeypatch):
    monkeypatch.setattr(environment.sys, "version_info", (3, 11, 9, "final", 0))
    monkeypatch.setattr(environment.platform, "python_version", lambda: "3.11.9")
    monkeypatch.setattr(environment, "_distribution_version", lambda package: environment.REQUIRED_PACKAGES[package])
    monkeypatch.setenv("ENVIRONMENT", "development")

    manifest = environment.ensure_runtime_environment(component="test")

    assert manifest["python_major_minor"] == "3.11"
    assert manifest["dependencies"]["fastapi"] == "0.128.8"
    assert manifest["fingerprint"]
    assert len(manifest["fingerprint"]) == 64


def test_runtime_validation_fails_for_unsupported_python(monkeypatch):
    monkeypatch.setattr(environment.sys, "version_info", (3, 10, 12, "final", 0))
    monkeypatch.setattr(environment.platform, "python_version", lambda: "3.10.12")
    monkeypatch.setattr(environment, "_distribution_version", lambda package: environment.REQUIRED_PACKAGES[package])
    monkeypatch.setenv("ENVIRONMENT", "development")

    with pytest.raises(RuntimeError, match="Python 3.11"):
        environment.ensure_runtime_environment(component="test")


def test_runtime_validation_fails_closed_in_strict_mode(monkeypatch):
    monkeypatch.setattr(environment.sys, "version_info", (3, 11, 9, "final", 0))
    monkeypatch.setattr(environment.platform, "python_version", lambda: "3.11.9")
    monkeypatch.setattr(environment, "_distribution_version", lambda package: environment.REQUIRED_PACKAGES[package])
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    with pytest.raises(RuntimeError, match="Missing required environment variable"):
        environment.ensure_runtime_environment(component="test")
