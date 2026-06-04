DEFAULT_ALLOWED_TOOLS = {
    "audio_agent",
    "code_agent",
    "sync_agent",
    "local_model",
    "memory",
    "syncmaster_analyze_metadata",
    "syncmaster_recommend_sync_fit",
    "syncmaster_match_brief",
    "syncmaster_save_track",
    "syncmaster_save_brief",
    "syncmaster_save_recommendation",
    "syncmaster_query_graph",
}


class PlanValidationError(ValueError):
    pass


def validate_plan(plan, max_steps=8, allowed_tools=None):
    allowed = set(allowed_tools or DEFAULT_ALLOWED_TOOLS)

    if not plan.id:
        raise PlanValidationError("plan id is required")
    if not plan.objective:
        raise PlanValidationError("plan objective is required")
    if not plan.steps:
        raise PlanValidationError("plan must include at least one step")
    if len(plan.steps) > max_steps:
        raise PlanValidationError(f"plan exceeds max steps: {max_steps}")

    step_ids = [step.id for step in plan.steps]
    if any(not step_id for step_id in step_ids):
        raise PlanValidationError("step ids are required")
    if len(step_ids) != len(set(step_ids)):
        raise PlanValidationError("step ids must be unique")

    known_ids = set(step_ids)
    graph = {}

    for step in plan.steps:
        if not step.description:
            raise PlanValidationError(f"step {step.id} description is required")
        if step.tool_name not in allowed:
            raise PlanValidationError(f"step {step.id} uses invalid tool: {step.tool_name}")

        graph[step.id] = []
        for dependency in step.dependencies:
            if dependency == step.id:
                raise PlanValidationError(f"step {step.id} cannot depend on itself")
            if dependency not in known_ids:
                raise PlanValidationError(
                    f"step {step.id} depends on unknown step: {dependency}"
                )
            graph[step.id].append(dependency)

    _assert_acyclic(graph)
    return plan


def _assert_acyclic(graph):
    visiting = set()
    visited = set()

    def visit(step_id):
        if step_id in visiting:
            raise PlanValidationError("plan contains a dependency cycle")
        if step_id in visited:
            return

        visiting.add(step_id)
        for dependency in graph[step_id]:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in graph:
        visit(step_id)
