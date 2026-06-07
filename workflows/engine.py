from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from tools.registry import ToolRegistry, ToolRegistryError


class WorkflowEngineError(ValueError):
    """Raised when a workflow is invalid or cannot be executed."""


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


class WorkflowEngine:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, steps: list[WorkflowStep | dict[str, Any]]) -> dict[str, Any]:
        """
        Execute a list of workflow steps in dependency order.
        
        Nested Workflow Tracing Policy:
        ------------------------------
        Each workflow execution (parent or nested) generates its own unique, internal workflow_id.
        Using contextvars context managers, the nested execution temporarily overrides the
        workflow_id context variable. Once the nested run completes, the parent workflow_id is
        restored automatically.
        """
        import uuid
        from app.core.tracing import set_workflow_id, reset_workflow_id, get_request_id

        # Generate workflow_id internally
        workflow_id = str(uuid.uuid4())
        token = set_workflow_id(workflow_id)


        try:
            normalized = [self._normalize_step(step) for step in steps]
            ordered = self._order_steps(normalized)
            outputs: dict[str, Any] = {}

            for step in ordered:
                resolved_args = self._resolve_value(step.args, outputs)
                outputs[step.id] = self.registry.execute(step.tool, resolved_args)

            req_id = get_request_id()
            self.execution_metadata = {
                "request_id": req_id,
                "workflow_id": workflow_id,
            }

            from app.core.tracing import assert_clean_outputs
            assert_clean_outputs(outputs)
            return outputs
        finally:

            reset_workflow_id(token)


    def validate(self, steps: list[WorkflowStep | dict[str, Any]]) -> list[WorkflowStep]:
        normalized = [self._normalize_step(step) for step in steps]
        self._order_steps(normalized)
        return normalized

    def _normalize_step(self, step: WorkflowStep | dict[str, Any]) -> WorkflowStep:
        if isinstance(step, WorkflowStep):
            normalized = step
        elif isinstance(step, dict):
            depends_on = step.get("depends_on", []) or []
            normalized = WorkflowStep(
                id=step.get("id", ""),
                tool=step.get("tool", ""),
                args=step.get("args", {}) or {},
                depends_on=depends_on,
            )
        else:
            raise WorkflowEngineError("Workflow steps must be WorkflowStep objects or dictionaries.")

        if not normalized.id or not isinstance(normalized.id, str):
            raise WorkflowEngineError("Workflow step id must be a non-empty string.")
        if not normalized.tool or not isinstance(normalized.tool, str):
            raise WorkflowEngineError(f"Workflow step {normalized.id} must define a tool.")
        if not isinstance(normalized.args, dict):
            raise WorkflowEngineError(f"Workflow step {normalized.id} args must be a dictionary.")
        if not isinstance(normalized.depends_on, list) or not all(
            isinstance(item, str) for item in normalized.depends_on
        ):
            raise WorkflowEngineError(f"Workflow step {normalized.id} depends_on must be a list of ids.")

        try:
            self.registry.get(normalized.tool)
        except ToolRegistryError as exc:
            raise WorkflowEngineError(str(exc)) from exc
        return normalized

    def _order_steps(self, steps: list[WorkflowStep]) -> list[WorkflowStep]:
        by_id = {}
        for step in steps:
            if step.id in by_id:
                raise WorkflowEngineError(f"Duplicate workflow step id: {step.id}")
            by_id[step.id] = step

        for step in steps:
            for dependency in step.depends_on:
                if dependency not in by_id:
                    raise WorkflowEngineError(
                        f"Workflow step {step.id} depends on unknown step: {dependency}"
                    )
            for dependency in _find_references(step.args):
                if dependency not in by_id:
                    raise WorkflowEngineError(
                        f"Workflow step {step.id} references unknown step: {dependency}"
                    )

        ordered: list[WorkflowStep] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in permanent:
                return
            if step_id in temporary:
                raise WorkflowEngineError(f"Workflow contains a dependency cycle at: {step_id}")

            temporary.add(step_id)
            step = by_id[step_id]
            dependencies = set(step.depends_on) | _find_references(step.args)
            for dependency in sorted(dependencies):
                visit(dependency)
            temporary.remove(step_id)
            permanent.add(step_id)
            ordered.append(step)

        for step in steps:
            visit(step.id)

        return ordered

    def _resolve_value(self, value: Any, outputs: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            if "$from" in value:
                source = value["$from"]
                if source not in outputs:
                    raise WorkflowEngineError(f"Step output is not available yet: {source}")
                return _extract_path(outputs[source], value.get("path"))
            return {key: self._resolve_value(item, outputs) for key, item in value.items()}

        if isinstance(value, list):
            return [self._resolve_value(item, outputs) for item in value]

        if isinstance(value, str):
            return _resolve_template(value, outputs)

        return value


REFERENCE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_-]+)(?:\.([a-zA-Z0-9_.-]+))?\s*\}\}")


def _find_references(value: Any) -> set[str]:
    references: set[str] = set()
    if isinstance(value, dict):
        source = value.get("$from")
        if isinstance(source, str):
            references.add(source)
        for item in value.values():
            references.update(_find_references(item))
    elif isinstance(value, list):
        for item in value:
            references.update(_find_references(item))
    elif isinstance(value, str):
        references.update(match.group(1) for match in REFERENCE_PATTERN.finditer(value))
    return references


def _resolve_template(value: str, outputs: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        step_id = match.group(1)
        path = match.group(2)
        if step_id not in outputs:
            raise WorkflowEngineError(f"Step output is not available yet: {step_id}")
        replacement = _extract_path(outputs[step_id], path)
        return str(replacement)

    return REFERENCE_PATTERN.sub(replace, value)


def _extract_path(value: Any, path: str | None) -> Any:
    if not path:
        return value

    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise WorkflowEngineError(f"Output path not found: {path}")
    return current
