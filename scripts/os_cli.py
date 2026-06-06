import argparse
import json
import os
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory.graph import MemoryGraph
from memory.learning import update_learning_state
from memory.log import record_feedback
from planning.providers import create_plan, select_planning_provider
from runtime.tasks import get_task, list_tasks, run_task, submit_task
from syncmaster.graph import save_brief, save_recommendation, save_track
from syncmaster.licensing import recommend_sync_fit
from syncmaster.matching import match_to_brief
from syncmaster.metadata import tag_metadata
from syncmaster.audio import analyze_audio_file
from tools.builtin import create_default_registry
from workflows.engine import WorkflowEngine


def plan_objective(objective: str, max_steps: Optional[int] = None) -> dict:
    registry = create_default_registry()
    provider = select_planning_provider()
    plan = create_plan(
        objective,
        provider=provider,
        max_steps=max_steps or int(os.getenv("PLANNER_MAX_STEPS", "8")),
        allowed_tools=registry.names(),
    )
    return plan.to_dict()


def run_objective(objective: str) -> dict:
    plan = plan_objective(objective)
    task = submit_task(
        objective,
        metadata={"planner_used": plan["provider"], "plan": plan},
    )
    return _run_planned_task(task)


def process_queue(limit: Optional[int] = None) -> list[dict]:
    queued = list_tasks(status="queued")
    if limit is not None:
        queued = queued[:limit]
    return [_run_planned_task(task) for task in queued]


def _run_planned_task(task: dict) -> dict:
    def execute():
        plan = task.get("metadata", {}).get("plan")
        if not plan:
            plan = plan_objective(task["task"])
        registry = create_default_registry()
        engine = WorkflowEngine(registry)
        outputs = engine.execute(_plan_steps_to_workflow(plan))
        _write_graph(task["task_id"], task["task"], plan, outputs)
        return {
            "plan": plan,
            "outputs": outputs,
            "final_output": outputs[plan["steps"][-1]["id"]] if plan["steps"] else None,
        }

    return run_task(task["task_id"], execute)


def _plan_steps_to_workflow(plan: dict) -> list[dict]:
    return [
        {
            "id": step["id"],
            "tool": step["tool_name"],
            "args": dict(step.get("inputs") or {}),
            "depends_on": list(step.get("dependencies") or []),
        }
        for step in plan.get("steps", [])
    ]


def _write_graph(task_id: str, objective: str, plan: dict, outputs: dict) -> None:
    graph = MemoryGraph()
    plan_id = plan["id"]
    graph.create_node(f"task:{task_id}", node_type="task", properties={"objective": objective})
    graph.create_node(f"plan:{plan_id}", node_type="plan", properties={"provider": plan["provider"]})
    graph.add_edge(f"task:{task_id}", "PLANNED_BY", f"plan:{plan_id}")

    for step in plan.get("steps", []):
        step_id = f"step:{task_id}:{step['id']}"
        tool_id = f"tool:{step['tool_name']}"
        graph.create_node(step_id, node_type="step", properties={"description": step.get("description")})
        graph.create_node(tool_id, node_type="tool", properties={"name": step["tool_name"]})
        graph.add_edge(f"plan:{plan_id}", "HAS_STEP", step_id)
        graph.add_edge(step_id, "CALLED_TOOL", tool_id)
        for dependency in step.get("dependencies", []):
            graph.add_edge(step_id, "DEPENDS_ON", f"step:{task_id}:{dependency}")
        if step["id"] in outputs:
            output_id = f"output:{task_id}:{step['id']}"
            graph.create_node(output_id, node_type="output", properties={"value": outputs[step["id"]]})
            graph.add_edge(step_id, "PRODUCED_OUTPUT", output_id)
            _write_syncmaster_graph_output(graph, step, outputs[step["id"]], output_id)


def _write_syncmaster_graph_output(graph: MemoryGraph, step: dict, output: dict, output_id: str) -> None:
    tool_name = step.get("tool_name")
    if tool_name == "syncmaster_analyze_metadata" and isinstance(output, dict):
        track = output.get("metadata")
        if isinstance(track, dict):
            node = save_track(track, graph=graph)
            graph.add_edge(node["id"], "HAS_METADATA_ANALYSIS", output_id)
    if tool_name == "syncmaster_recommend_sync_fit" and isinstance(output, dict):
        node = save_recommendation(output, graph=graph)
        graph.add_edge(node["id"], "PRODUCED_FROM", output_id)


def memory_search(query: str) -> dict:
    graph = MemoryGraph()
    query_lower = query.lower()
    matches = []
    for node in graph.list_nodes():
        serialized = json.dumps(node, sort_keys=True).lower()
        if query_lower in serialized:
            matches.append(node)
    return {"query": query, "matches": matches}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dakol AI OS command line")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _objective_command(subparsers, "plan")
    _objective_command(subparsers, "run")
    _objective_command(subparsers, "queue")

    process_parser = subparsers.add_parser("process-queue")
    process_parser.add_argument("--limit", type=int)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("task_id")

    subparsers.add_parser("tasks")
    subparsers.add_parser("learn")

    feedback_parser = subparsers.add_parser("feedback")
    feedback_parser.add_argument("event_id")
    feedback_parser.add_argument("feedback")
    feedback_parser.add_argument("--note")

    memory_parser = subparsers.add_parser("memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_search_parser = memory_subparsers.add_parser("search")
    memory_search_parser.add_argument("query")

    syncmaster_parser = subparsers.add_parser("syncmaster")
    syncmaster_subparsers = syncmaster_parser.add_subparsers(dest="syncmaster_command", required=True)
    analyze_parser = syncmaster_subparsers.add_parser("analyze-metadata")
    analyze_parser.add_argument("--payload-json", required=True)
    analyze_audio_parser = syncmaster_subparsers.add_parser("analyze-audio")
    analyze_audio_parser.add_argument("--audio-path", required=True)
    analyze_audio_parser.add_argument("--payload-json", default="{}")
    recommend_parser = syncmaster_subparsers.add_parser("recommend-fit")
    recommend_parser.add_argument("--track-json", required=True)
    recommend_parser.add_argument("--brief-json", required=True)
    match_parser = syncmaster_subparsers.add_parser("match-brief")
    match_parser.add_argument("--brief-json", required=True)
    match_parser.add_argument("--candidates-json", required=True)
    match_parser.add_argument("--limit", type=int)
    save_track_parser = syncmaster_subparsers.add_parser("save-track")
    save_track_parser.add_argument("--track-json", required=True)
    save_track_parser.add_argument("--track-id")
    save_brief_parser = syncmaster_subparsers.add_parser("save-brief")
    save_brief_parser.add_argument("--brief-json", required=True)
    save_brief_parser.add_argument("--brief-id")
    save_recommendation_parser = syncmaster_subparsers.add_parser("save-recommendation")
    save_recommendation_parser.add_argument("--recommendation-json", required=True)
    save_recommendation_parser.add_argument("--track-id")
    save_recommendation_parser.add_argument("--brief-id")
    save_recommendation_parser.add_argument("--recommendation-id")

    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            result = plan_objective(args.objective)
        elif args.command == "run":
            result = run_objective(args.objective)
        elif args.command == "queue":
            plan = plan_objective(args.objective)
            result = submit_task(args.objective, metadata={"planner_used": plan["provider"], "plan": plan})
        elif args.command == "process-queue":
            result = process_queue(args.limit)
        elif args.command == "status":
            result = get_task(args.task_id) or {"error": f"No task found for task_id: {args.task_id}"}
        elif args.command == "tasks":
            result = list_tasks()
        elif args.command == "learn":
            result = update_learning_state()
        elif args.command == "feedback":
            result = record_feedback(args.event_id, args.feedback, args.note)
        elif args.command == "memory" and args.memory_command == "search":
            result = memory_search(args.query)
        elif args.command == "syncmaster":
            result = _handle_syncmaster_command(args)
        else:
            parser.error("unsupported command")
    except ValueError as exc:
        sys.stdout.write(json.dumps({"error": str(exc)}, indent=2) + "\n")
        return 1

    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


def _objective_command(subparsers, name: str) -> None:
    command = subparsers.add_parser(name)
    command.add_argument("objective")


def _handle_syncmaster_command(args) -> dict:
    if args.syncmaster_command == "analyze-metadata":
        return tag_metadata(payload=_parse_json_arg(args.payload_json))
    if args.syncmaster_command == "analyze-audio":
        return analyze_audio_file(args.audio_path, payload=_parse_json_arg(args.payload_json))
    if args.syncmaster_command == "recommend-fit":
        return recommend_sync_fit(_parse_json_arg(args.track_json), _parse_json_arg(args.brief_json))
    if args.syncmaster_command == "match-brief":
        candidates = _parse_json_arg(args.candidates_json)
        candidate_items = candidates.get("candidates")
        if not isinstance(candidate_items, list):
            raise ValueError("candidates JSON must contain a candidates array")
        return {
            "matches": match_to_brief(
                _parse_json_arg(args.brief_json),
                candidate_items,
                limit=args.limit,
            )
        }
    if args.syncmaster_command == "save-track":
        return save_track(_parse_json_arg(args.track_json), track_id=args.track_id)
    if args.syncmaster_command == "save-brief":
        return save_brief(_parse_json_arg(args.brief_json), brief_id=args.brief_id)
    if args.syncmaster_command == "save-recommendation":
        return save_recommendation(
            _parse_json_arg(args.recommendation_json),
            track_id=args.track_id,
            brief_id=args.brief_id,
            recommendation_id=args.recommendation_id,
        )
    raise ValueError(f"Unsupported SyncMaster command: {args.syncmaster_command}")


def _parse_json_arg(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON argument must be an object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
