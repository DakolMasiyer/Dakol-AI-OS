import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppManifest:
    app_id: str
    allowed_capabilities: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    policy_scope: str = "isolated"
    trace_namespace: str = "isolated"
    execution_profile: str = "standard"
    replay_policy: str = "strict"
    trace_retention_policy: str = "30_days"

    @classmethod
    def from_file(cls, path: Path) -> "AppManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            app_id=data["app_id"],
            allowed_capabilities=data.get("allowed_capabilities", []),
            allowed_tools=data.get("allowed_tools", []),
            policy_scope=data.get("policy_scope", "isolated"),
            trace_namespace=data.get("trace_namespace", "isolated"),
            execution_profile=data.get("execution_profile", "standard"),
            replay_policy=data.get("replay_policy", "strict"),
            trace_retention_policy=data.get("trace_retention_policy", "30_days"),
        )
