from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_version_file_is_standardized():
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.11"


def test_requirements_are_segmented():
    prod = (ROOT / "requirements-prod.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    base = (ROOT / "requirements-base.txt").read_text(encoding="utf-8")
    lock = (ROOT / "requirements-lock.txt").read_text(encoding="utf-8")

    assert "-r requirements-base.txt" in prod
    assert "-c requirements-lock.txt" in prod
    assert "-r requirements-base.txt" in dev
    assert "-c requirements-lock.txt" in dev
    assert "pytest==" in dev
    assert "pytest-cov==" in dev
    assert "fastapi==" in base
    assert "slowapi==" in base
    assert "requests==" in base
    assert "slowapi==0.1.9" in lock
    assert "pytest==8.4.2" in lock
    assert "pytest-cov==6.2.1" in lock


def test_dockerfile_uses_prod_requirements():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements-prod.txt" in dockerfile


def test_requirements_base_is_locked():
    base = (ROOT / "requirements-base.txt").read_text(encoding="utf-8")
    assert "-c requirements-lock.txt" in base


def test_ci_uses_python_311():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'python-version: "3.11"' in ci
