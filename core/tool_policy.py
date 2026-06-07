from typing import Any
import logging

import importlib.util
import sys
from pathlib import Path

def _get_registry():
    if "platform.app_registry" in sys.modules:
        return sys.modules["platform.app_registry"].AppRegistry
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("platform.app_registry", root / "platform" / "app_registry.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["platform.app_registry"] = mod
    spec.loader.exec_module(mod)
    return mod.AppRegistry

logger = logging.getLogger(__name__)

class ToolPolicyViolation(Exception):
    """Raised when an app attempts to use an unauthorized tool."""


def verify_tool_execution(app_id: str, tool_name: str) -> None:
    """Verify if the given app_id is allowed to execute the given tool."""
    try:
        registry = _get_registry()
        manifest = registry.get_manifest(app_id)
    except ValueError as exc:
        logger.error(f"Failed to find manifest for app {app_id}")
        raise ToolPolicyViolation(f"App {app_id} is not registered or manifest missing.") from exc

    if tool_name not in manifest.allowed_tools:
        logger.error(f"App {app_id} attempted unauthorized execution of tool: {tool_name}")
        raise ToolPolicyViolation(f"App {app_id} is not authorized to execute tool '{tool_name}'.")
