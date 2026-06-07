from typing import Any

import core.api


class AppRuntimeAdapter:
    def __init__(self, app_id: str):
        self.app_id = app_id

    def execute_task(self, task: str, **kwargs: Any) -> Any:
        return core.api.execute_task(task, app_id=self.app_id, **kwargs)

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return core.api.execute_tool(tool_name, arguments, app_id=self.app_id)
