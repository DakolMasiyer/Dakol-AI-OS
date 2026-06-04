from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class ToolRegistryError(ValueError):
    """Raised when a tool cannot be registered or executed."""


class ToolValidationError(ToolRegistryError):
    """Raised when a tool call does not satisfy the tool schema."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: dict[str, Any] = field(default_factory=dict)

    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ToolValidationError(f"Arguments for {self.name} must be a dictionary.")

        schema = self.input_schema or {}
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)

        for field_name in required:
            if field_name not in arguments:
                raise ToolValidationError(f"Missing required argument for {self.name}: {field_name}")

        if not additional:
            allowed = set(properties)
            unexpected = sorted(set(arguments) - allowed)
            if unexpected:
                joined = ", ".join(unexpected)
                raise ToolValidationError(f"Unexpected argument(s) for {self.name}: {joined}")

        for field_name, value in arguments.items():
            if field_name not in properties:
                continue
            expected_type = properties[field_name].get("type")
            if expected_type and not _matches_type(value, expected_type):
                raise ToolValidationError(
                    f"Argument {field_name} for {self.name} must be {expected_type}."
                )

    def execute(self, arguments: dict[str, Any] | None = None) -> Any:
        arguments = arguments or {}
        self.validate(arguments)
        return self.handler(**arguments)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if not tool.name or not isinstance(tool.name, str):
            raise ToolRegistryError("Tool name must be a non-empty string.")
        if tool.name in self._tools:
            raise ToolRegistryError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def register_function(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        input_schema: dict[str, Any] | None = None,
    ) -> Tool:
        return self.register(
            Tool(
                name=name,
                description=description,
                handler=handler,
                input_schema=input_schema or {},
            )
        )

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRegistryError(f"Unknown tool: {name}") from exc

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.get(name).execute(arguments)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def names(self) -> set[str]:
        return set(self._tools)


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(_matches_single_type(value, item) for item in expected_types)


def _matches_single_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "null":
        return value is None
    return True
