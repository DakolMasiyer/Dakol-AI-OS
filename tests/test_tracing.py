import contextvars
import json
import logging
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.tracing import (
    get_request_id,
    get_workflow_id,
    set_request_id,
    set_workflow_id,
    reset_request_id,
    reset_workflow_id,
    TracingMiddleware,
)
from app.core.logging import JsonLogFormatter
from workflows.engine import WorkflowEngine, WorkflowStep
from tools.registry import ToolRegistry
from runtime.tasks import submit_task, load_tasks
from skills.model_router import generate_with_fallback, AllModelsUnavailableError


class TracingTests(unittest.TestCase):
    def setUp(self):
        # Reset context variables before each test
        self.req_token = set_request_id("")
        self.work_token = set_workflow_id("")

    def tearDown(self):
        reset_request_id(self.req_token)
        reset_workflow_id(self.work_token)

    def test_contextvars_get_set(self):
        """Test basic setting and getting of tracing context variables."""
        set_request_id("test-req-123")
        set_workflow_id("test-work-456")
        self.assertEqual(get_request_id(), "test-req-123")
        self.assertEqual(get_workflow_id(), "test-work-456")

    def test_thread_pool_executor_propagation(self):
        """Test contextvars propagation through ThreadPoolExecutor using copy_context().run."""
        set_request_id("propagate-req-id")
        set_workflow_id("propagate-work-id")

        def worker_func():
            return get_request_id(), get_workflow_id()

        ctx = contextvars.copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ctx.run, worker_func)
            thread_req_id, thread_work_id = future.result()

        self.assertEqual(thread_req_id, "propagate-req-id")
        self.assertEqual(thread_work_id, "propagate-work-id")

    def test_json_logging_formatter_with_tracing(self):
        """Test that JsonLogFormatter automatically extracts and appends context variables."""
        set_request_id("log-req-789")
        set_workflow_id("log-work-012")

        formatter = JsonLogFormatter()
        logger = logging.getLogger("test_logger")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test_file.py",
            lno=10,
            msg="Logging test message",
            args=(),
            exc_info=None,
        )

        formatted_json = formatter.format(record)
        data = json.loads(formatted_json)

        self.assertEqual(data["request_id"], "log-req-789")
        self.assertEqual(data["workflow_id"], "log-work-012")
        self.assertEqual(data["message"], "Logging test message")

    def test_tracing_middleware(self):
        """Test that TracingMiddleware generates and exposes IDs through response headers only."""
        app = FastAPI()
        app.add_middleware(TracingMiddleware)

        @app.get("/test-route")
        def route():
            # Internal context check
            return {
                "in_ctx_request_id": get_request_id(),
                "in_ctx_workflow_id": get_workflow_id(),
            }

        client = TestClient(app)

        # 1. Test without X-Request-ID header: middleware generates new request ID
        response = client.get("/test-route")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response.headers)
        
        # Parse generated request_id
        generated_id = response.headers["X-Request-ID"]
        self.assertTrue(len(generated_id) > 10)
        
        # Verify JSON body does NOT contain request_id/workflow_id automatically
        body = response.json()
        self.assertNotIn("request_id", body)
        self.assertNotIn("workflow_id", body)
        self.assertEqual(body["in_ctx_request_id"], generated_id)

        # 2. Test propagating custom X-Request-ID header
        custom_id = "my-custom-uuid"
        response2 = client.get("/test-route", headers={"X-Request-ID": custom_id})
        self.assertEqual(response2.headers["X-Request-ID"], custom_id)
        self.assertEqual(response2.json()["in_ctx_request_id"], custom_id)

    def test_internal_workflow_id_generation(self):
        """Test that workflow IDs are generated internally inside WorkflowEngine.execute."""
        registry = ToolRegistry()
        
        def dummy_tool(val: str):
            # Assert context variables exist inside step execution
            self.assertEqual(get_request_id(), "req-for-workflow")
            self.assertIsNotNone(get_workflow_id())
            return f"processed-{val}"

        registry.register_function(
            name="test_tool",
            description="A dummy test tool",
            handler=dummy_tool,
            input_schema={
                "type": "object",
                "required": ["val"],
                "properties": {"val": {"type": "string"}},
            }
        )


        set_request_id("req-for-workflow")
        engine = WorkflowEngine(registry)
        
        steps = [
            WorkflowStep(id="step1", tool="test_tool", args={"val": "hello"})
        ]
        
        outputs = engine.execute(steps)
        self.assertEqual(outputs["step1"], "processed-hello")
        self.assertNotIn("_request_id", outputs)
        self.assertNotIn("_workflow_id", outputs)
        self.assertEqual(engine.execution_metadata["request_id"], "req-for-workflow")
        self.assertIsNotNone(engine.execution_metadata["workflow_id"])


    def test_task_submission_metadata_tracing(self):
        """Test that submit_task saves active trace context parameters into tasks metadata."""
        set_request_id("submit-task-req")
        set_workflow_id("submit-task-work")

        task = submit_task("Run music sync matching", metadata={"custom_info": "yes"})
        
        self.assertEqual(task["metadata"]["request_id"], "submit-task-req")
        self.assertEqual(task["metadata"]["workflow_id"], "submit-task-work")
        self.assertEqual(task["metadata"]["custom_info"], "yes")

    def test_model_observability_logging(self):
        """Test model observability cost metrics estimation helper."""
        from skills.model_router import _estimate_cost, MODEL_PRICING
        
        groq_cost = _estimate_cost("groq", 1000)
        gemini_cost = _estimate_cost("gemini", 1000)
        
        self.assertAlmostEqual(groq_cost, 0.0007)
        self.assertAlmostEqual(gemini_cost, 0.00015)

        # 1. unknown provider returns None
        self.assertIsNone(_estimate_cost("unknown-provider", 1000))
        
        # 2. token_count=None returns None
        self.assertIsNone(_estimate_cost("groq", None))

        # 3. missing pricing env returns None
        original_pricing = MODEL_PRICING.copy()
        try:
            if "groq" in MODEL_PRICING:
                del MODEL_PRICING["groq"]
            self.assertIsNone(_estimate_cost("groq", 1000))
        finally:
            MODEL_PRICING.clear()
            MODEL_PRICING.update(original_pricing)

    def test_concurrency_stress_test_and_isolation(self):
        """Test isolation and uniqueness of request IDs under high concurrency (100 parallel requests)."""
        import queue
        import time
        
        request_ids_collected = queue.Queue()
        
        def simulate_request(req_num: int):
            req_id = f"concurrent-req-{req_num}-{uuid.uuid4()}"
            token = set_request_id(req_id)
            try:
                time.sleep(0.005)
                self.assertEqual(get_request_id(), req_id)
                request_ids_collected.put(req_id)
            finally:
                reset_request_id(token)

        num_requests = 100
        with ThreadPoolExecutor(max_workers=50) as pool:
            pool.map(simulate_request, range(num_requests))

        results = []
        while not request_ids_collected.empty():
            results.append(request_ids_collected.get())

        self.assertEqual(len(results), num_requests)
        self.assertEqual(len(set(results)), num_requests)

    def test_nested_workflow_id_propagation(self):
        """Test that nested workflows receive distinct IDs and restore parent IDs on completion."""
        registry = ToolRegistry()
        nested_engine = WorkflowEngine(registry)

        nested_workflow_ids = []

        registry.register_function(
            name="nested_step_tool",
            description="Tool executed inside the nested workflow",
            handler=lambda val: nested_workflow_ids.append(get_workflow_id()),
            input_schema={
                "type": "object",
                "required": ["val"],
                "properties": {"val": {"type": "string"}},
            }
        )

        registry.register_function(
            name="parent_step_tool",
            description="Tool executed inside the parent workflow, launching a nested one",
            handler=lambda val: nested_engine.execute([
                WorkflowStep(id="nested_step", tool="nested_step_tool", args={"val": val})
            ]),
            input_schema={
                "type": "object",
                "required": ["val"],
                "properties": {"val": {"type": "string"}},
            }
        )

        parent_engine = WorkflowEngine(registry)
        parent_outputs = parent_engine.execute([
            WorkflowStep(id="parent_step", tool="parent_step_tool", args={"val": "data"})
        ])

        parent_work_id = parent_engine.execution_metadata["workflow_id"]
        
        # Verify nested workflow ran with a distinct workflow ID
        self.assertEqual(len(nested_workflow_ids), 1)
        nested_work_id = nested_workflow_ids[0]
        
        self.assertIsNotNone(nested_work_id)
        self.assertNotEqual(parent_work_id, nested_work_id)

    def test_outputs_cleanliness_guards(self):
        """Test that schema guards raise AssertionError if metadata leakage is detected."""
        from app.core.tracing import assert_clean_outputs
        
        # Test direct helper behavior
        assert_clean_outputs({"clean_key": "val"})
        with self.assertRaises(AssertionError):
            assert_clean_outputs({"_request_id": "req-123"})
        with self.assertRaises(AssertionError):
            assert_clean_outputs({"_workflow_id": "work-123"})

        # Test Workflow exit boundary guard
        registry = ToolRegistry()
        registry.register_function(
            name="leak_tool",
            description="Leaky tool",
            handler=lambda val: {"_request_id": "leak"},
            input_schema={
                "type": "object",
                "required": ["val"],
                "properties": {"val": {"type": "string"}},
            }
        )
        engine = WorkflowEngine(registry)
        steps = [WorkflowStep(id="step1", tool="leak_tool", args={"val": "hello"})]
        with self.assertRaises(AssertionError):
            engine.execute(steps)

        # Test API response serialization boundary guard
        app = FastAPI()
        app.add_middleware(TracingMiddleware)

        @app.get("/leak-route")
        def leak_route():
            return {"nested": {"_workflow_id": "leak"}}

        client = TestClient(app)
        
        # 1. Default Mode (OBSERVABILITY): Logs error but does NOT raise or block response
        response = client.get("/leak-route")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"nested": {"_workflow_id": "leak"}})

        # 2. STRICT Mode: Raises AssertionError and propagates to client/fail request
        import app.core.tracing
        original_mode = app.core.tracing.VALIDATION_MODE
        app.core.tracing.VALIDATION_MODE = "STRICT"
        try:
            with self.assertRaises(AssertionError):
                client.get("/leak-route")
        finally:
            app.core.tracing.VALIDATION_MODE = original_mode



