from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from importlib import metadata
from typing import Any, Mapping


SUPPORTED_PYTHON_MAJOR_MINOR = (3, 11)

REQUIRED_PACKAGES = {
    "anyio": "4.12.1",
    "fastapi": "0.128.8",
    "google-genai": "1.47.0",
    "httpx": "0.28.1",
    "pydantic": "2.13.4",
    "PyJWT": "2.13.0",
    "python-dotenv": "1.2.1",
    "requests": "2.32.5",
    "slowapi": "0.1.9",
    "supabase": "2.30.1",
    "uvicorn": "0.39.0",
}

STRICT_ENVIRONMENTS = {"cloudrun", "production"}
REQUIRED_STRICT_ENV_VARS = ("PORT", "SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_JWT_SECRET")
OPTIONAL_SHARED_ENV_VARS = ("FLUTTERWAVE_ROUTER_URL",)


def _distribution_version(package_name: str) -> str:
    return metadata.version(package_name)


def _runtime_environment_name() -> str:
    return os.getenv("ENVIRONMENT", "development").strip().lower()


def _runtime_container_id() -> str:
    return (
        os.getenv("K_REVISION")
        or os.getenv("K_SERVICE")
        or os.getenv("REVISION_ID")
        or os.getenv("CI_JOB_ID")
        or os.getenv("GITHUB_RUN_ID")
        or os.getenv("HOSTNAME")
        or ""
    )


def _runtime_git_sha() -> str:
    return (
        os.getenv("GITHUB_SHA")
        or os.getenv("CI_COMMIT_SHA")
        or os.getenv("COMMIT_SHA")
        or ""
    )


def _runtime_strict_flag() -> bool:
    explicit = os.getenv("RUNTIME_STRICT", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    return _runtime_environment_name() in STRICT_ENVIRONMENTS


def build_runtime_manifest(component: str = "web") -> dict[str, Any]:
    dependencies = {
        package: _distribution_version(package)
        for package in REQUIRED_PACKAGES
        if _distribution_version(package)
    }
    manifest = {
        "component": component,
        "environment": _runtime_environment_name(),
        "container_id": _runtime_container_id(),
        "git_sha": _runtime_git_sha(),
        "interpreter": sys.executable,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_major_minor": f"{sys.version_info[0]}.{sys.version_info[1]}",
        "dependencies": dependencies,
        "strict_mode": _runtime_strict_flag(),
        "required_env_vars": {
            name: bool(os.getenv(name, "").strip())
            for name in REQUIRED_STRICT_ENV_VARS
        },
        "shared_service_urls": {
            name: os.getenv(name, "").strip()
            for name in OPTIONAL_SHARED_ENV_VARS
            if os.getenv(name, "").strip()
        },
    }
    manifest["fingerprint"] = runtime_fingerprint(manifest)
    return manifest


def runtime_fingerprint(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("fingerprint", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ensure_runtime_environment(component: str = "web") -> dict[str, Any]:
    errors: list[str] = []

    major_minor = (sys.version_info[0], sys.version_info[1])
    if major_minor != SUPPORTED_PYTHON_MAJOR_MINOR:
        errors.append(
            f"Python {SUPPORTED_PYTHON_MAJOR_MINOR[0]}.{SUPPORTED_PYTHON_MAJOR_MINOR[1]} is required, "
            f"found {platform.python_version()}"
        )

    dependency_versions = {}
    for package_name, expected_version in REQUIRED_PACKAGES.items():
        try:
            actual_version = _distribution_version(package_name)
            dependency_versions[package_name] = actual_version
        except metadata.PackageNotFoundError:
            errors.append(f"Missing required dependency: {package_name}")
            continue

        if actual_version != expected_version:
            errors.append(
                f"Dependency version mismatch for {package_name}: "
                f"expected {expected_version}, found {actual_version}"
            )

    if _runtime_strict_flag():
        for env_var in REQUIRED_STRICT_ENV_VARS:
            if not os.getenv(env_var, "").strip():
                errors.append(f"Missing required environment variable: {env_var}")

    if errors:
        raise RuntimeError("Runtime validation failed:\n- " + "\n- ".join(errors))

    manifest = build_runtime_manifest(component=component)
    manifest["dependencies"] = dependency_versions
    return manifest
