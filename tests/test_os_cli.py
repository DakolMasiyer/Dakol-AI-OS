import json
import math
import struct
import tempfile
import unittest
import wave
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts import os_cli


class OsCliTests(unittest.TestCase):
    def test_plan_command_returns_structured_plan(self):
        with patch.dict("os.environ", {"PLANNING_PROVIDER": "deterministic", "PLANNER_USE_CACHE": "false"}):
            output = StringIO()
            with redirect_stdout(output):
                exit_code = os_cli.main(["plan", "debug the router"])

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["provider"], "deterministic")
        self.assertTrue(result["steps"])

    def test_run_command_persists_task_and_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            graph_path = str(Path(temp_dir) / "graph.json")

            with patch("runtime.tasks.TASKS_FILE", tasks_path), patch("memory.graph.GRAPH_FILE", graph_path):
                with patch.dict("os.environ", {"PLANNING_PROVIDER": "deterministic", "PLANNER_USE_CACHE": "false"}):
                    output = StringIO()
                    with redirect_stdout(output):
                        exit_code = os_cli.main(["run", "debug the router"])

            result = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "completed")
            self.assertTrue(Path(tasks_path).exists())
            self.assertTrue(Path(graph_path).exists())

    def test_process_queue_runs_queued_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            graph_path = str(Path(temp_dir) / "graph.json")

            with patch("runtime.tasks.TASKS_FILE", tasks_path), patch("memory.graph.GRAPH_FILE", graph_path):
                with patch.dict("os.environ", {"PLANNING_PROVIDER": "deterministic", "PLANNER_USE_CACHE": "false"}):
                    with redirect_stdout(StringIO()):
                        os_cli.main(["queue", "debug the router"])
                    output = StringIO()
                    with redirect_stdout(output):
                        exit_code = os_cli.main(["process-queue"])

            result = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result[0]["status"], "completed")

    def test_memory_search_reads_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = str(Path(temp_dir) / "graph.json")

            with patch("memory.graph.GRAPH_FILE", graph_path):
                os_cli._write_graph(
                    "task-1",
                    "debug router",
                    {
                        "id": "plan_debug",
                        "provider": "deterministic",
                        "steps": [
                            {
                                "id": "step_1",
                                "tool_name": "local_model",
                                "description": "debug",
                                "dependencies": [],
                            }
                        ],
                    },
                    {"step_1": {"ok": True}},
                )
                result = os_cli.memory_search("debug router")

            self.assertEqual(result["matches"][0]["type"], "task")

    def test_syncmaster_analyze_metadata_cli(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = os_cli.main(
                [
                    "syncmaster",
                    "analyze-metadata",
                    "--payload-json",
                    '{"description":"Dark cinematic 120 bpm instrumental strings"}',
                ]
            )

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["metadata"]["bpm"], 120)
        self.assertIn("cinematic", result["metadata"]["genre"])

    def test_syncmaster_analyze_audio_cli(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "night_lift.wav"
            _write_click_wav(audio_path, bpm=100)

            output = StringIO()
            with redirect_stdout(output):
                exit_code = os_cli.main(
                    [
                        "syncmaster",
                        "analyze-audio",
                        "--audio-path",
                        str(audio_path),
                        "--payload-json",
                        '{"description":"Calm cinematic instrumental"}',
                    ]
                )

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertAlmostEqual(result["audio"]["estimated_bpm"], 100, delta=8)
        self.assertIn("cinematic", result["metadata"]["metadata"]["genre"])

    def test_syncmaster_save_track_cli_writes_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = str(Path(temp_dir) / "graph.json")

            with patch("memory.graph.GRAPH_FILE", graph_path):
                output = StringIO()
                with redirect_stdout(output):
                    exit_code = os_cli.main(
                        [
                            "syncmaster",
                            "save-track",
                            "--track-json",
                            '{"title":"Night Lift","composer":"Dakol"}',
                            "--track-id",
                            "night_lift",
                        ]
                    )

            result = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["id"], "track:night_lift")
            self.assertTrue(Path(graph_path).exists())

    def test_syncmaster_match_brief_cli(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = os_cli.main(
                [
                    "syncmaster",
                    "match-brief",
                    "--brief-json",
                    '{"genres":["cinematic"],"moods":["dark"],"min_bpm":110,"max_bpm":125}',
                    "--candidates-json",
                    '{"candidates":[{"id":"a","title":"Night Lift","genres":["cinematic"],"moods":["dark"],"bpm":120},{"id":"b","title":"Sunny Loop","genres":["pop"],"moods":["bright"],"bpm":90}]}',
                    "--limit",
                    "1",
                ]
            )

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["matches"][0]["candidate"]["id"], "a")

    def test_syncmaster_cli_reports_malformed_json(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = os_cli.main(
                [
                    "syncmaster",
                    "analyze-metadata",
                    "--payload-json",
                    "{bad json",
                ]
            )

        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid JSON", result["error"])


if __name__ == "__main__":
    unittest.main()


def _write_click_wav(path: Path, bpm: int, seconds: float = 2.5, sample_rate: int = 8000) -> None:
    beat_interval = 60 / bpm
    total_frames = int(seconds * sample_rate)
    samples = []
    for index in range(total_frames):
        t = index / sample_rate
        beat_position = t % beat_interval
        value = 20000 if beat_position < 0.025 else int(500 * math.sin(2 * math.pi * 220 * t))
        samples.append(struct.pack("<h", value))

    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"".join(samples))
