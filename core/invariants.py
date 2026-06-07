import threading
import inspect

# Execution active context flag to verify learning system isolation
_execution_active = threading.local()


def is_in_execution_path() -> bool:
    return getattr(_execution_active, "active", False)


class ExecutionPathContext:
    def __enter__(self):
        _execution_active.active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _execution_active.active = False


def assert_routing_determinism(task: str, decision_before, decision_after):
    """
    Assert routing determinism by comparing two decisions for the same task.
    """
    if (decision_before.model != decision_after.model or 
        decision_before.intent != decision_after.intent or 
        decision_before.route != decision_after.route or 
        decision_before.execution_target != decision_after.execution_target):
        raise AssertionError(f"Routing determinism violation for task '{task}'!")


def assert_agent_immutability(agents=None):
    """
    Assert no runtime mutation of agents.
    """
    if agents is None:
        from agents.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        agents = orchestrator.agents

    for agent in agents:
        if agent.domain_weight != agent.base_weight:
            raise AssertionError(f"Agent {agent.name} domain_weight mutated!")
        if not isinstance(agent.base_weight, (int, float)):
            raise AssertionError(f"base_weight of {agent.name} is not numeric!")
        if hasattr(agent, "learning_multiplier"):
            raise AssertionError(f"Agent {agent.name} has learning_multiplier!")
        if hasattr(agent, "base_domain_weight"):
            raise AssertionError(f"Agent {agent.name} has base_domain_weight!")


def assert_learning_is_advisory_only():
    """
    Assert learning state is not accessed during execution path.
    """
    if is_in_execution_path():
        try:
            from memory.learning import get_learning_recommendations
            get_learning_recommendations()
            raise AssertionError("Advisory violation: learning state accessed in execution path without error!")
        except RuntimeError as e:
            if str(e) != "LEARNING SYSTEM VIOLATION":
                raise AssertionError(f"Advisory violation: unexpected error {e}")


def assert_no_learning_state_direct_access(caller_module: str = None):
    """
    Enforce that NO module except memory/learning.py (or tests) may import or parse learning_state.json directly.
    """
    if caller_module is None:
        stack = inspect.stack()
        caller_frame = None
        for frame_info in stack[1:]:
            mod_name = frame_info.frame.f_globals.get("__name__", "")
            if mod_name and not mod_name.startswith("core.invariants"):
                caller_frame = frame_info
                break
        if caller_frame:
            caller_module = caller_frame.frame.f_globals.get("__name__", "")
        else:
            caller_module = "unknown"

    # Allow memory.learning, core.invariants, and tests to load the state
    if not (caller_module.startswith("memory.learning") or 
            caller_module.startswith("tests") or 
            caller_module.startswith("core.invariants")):
        raise RuntimeError(f"DIRECT ACCESS VIOLATION: Module '{caller_module}' attempted direct access to learning state.")
