"""Unit tests for RunManager service and cross-device active run streaming."""

import asyncio
import unittest

from fastapi.testclient import TestClient

from remote_code_agent.server import app
from remote_code_agent.services.run_manager import (
    ActiveRun,
    RunAlreadyInProgressError,
    RunManager,
)


class TestRunManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = RunManager()

    def test_get_active_run_empty(self):
        active = self.manager.get_active_run()
        self.assertFalse(active["active"])
        self.assertEqual(active["status"], "idle")
        self.assertEqual(active["logs"], "")
        self.assertIsNone(active["run_id"])

    async def test_start_run_and_stream_completion(self):
        async def mock_generator(prompt, project_name=None):
            yield f"Starting {project_name}\n"
            await asyncio.sleep(0.01)
            yield f"Working on {prompt}\n"
            await asyncio.sleep(0.01)
            yield "Finished!\n"

        run = self.manager.start_run(
            prompt="Build feature",
            project_name="demo-proj",
            generator_fn=mock_generator,
        )
        self.assertIsInstance(run, ActiveRun)
        self.assertEqual(run.status, "running")

        # Collect stream output
        chunks = []
        async for chunk in self.manager.stream_run(run.run_id):
            chunks.append(chunk)

        full_output = "".join(chunks)
        self.assertIn("Starting demo-proj", full_output)
        self.assertIn("Working on Build feature", full_output)
        self.assertIn("Finished!", full_output)

        # Verify final manager state
        active = self.manager.get_active_run()
        self.assertFalse(active["active"])
        self.assertEqual(active["status"], "completed")
        self.assertIn("Finished!", active["logs"])

    async def test_multi_subscriber_fanout(self):
        async def slow_generator(prompt, project_name=None):
            for i in range(3):
                await asyncio.sleep(0.01)
                yield f"step_{i};"

        run = self.manager.start_run(
            prompt="step test",
            project_name="step-proj",
            generator_fn=slow_generator,
        )

        async def subscriber():
            out = []
            async for chunk in self.manager.stream_run(run.run_id):
                out.append(chunk)
            return "".join(out)

        # Two concurrent listeners (e.g. desktop and mobile)
        res1, res2 = await asyncio.gather(subscriber(), subscriber())
        self.assertEqual(res1, "step_0;step_1;step_2;")
        self.assertEqual(res2, "step_0;step_1;step_2;")

    async def test_stream_replay_with_offset(self):
        async def fast_generator(prompt, project_name=None):
            yield "CHUNK_A"
            yield "CHUNK_B"
            yield "CHUNK_C"

        run = self.manager.start_run(
            prompt="test offset",
            project_name="offset-proj",
            generator_fn=fast_generator,
        )
        # Wait for completion
        await run.task

        # Total logs: "CHUNK_ACHUNK_BCHUNK_C" (length 21)
        full_logs = "".join(run.logs)
        self.assertEqual(full_logs, "CHUNK_ACHUNK_BCHUNK_C")

        # Replay with offset 7 (skip "CHUNK_A")
        replayed = []
        async for chunk in self.manager.stream_run(run.run_id, offset=7):
            replayed.append(chunk)

        self.assertEqual("".join(replayed), "CHUNK_BCHUNK_C")

    async def test_run_already_in_progress(self):
        async def hanging_generator(prompt, project_name=None):
            await asyncio.sleep(1.0)
            yield "done"

        run1 = self.manager.start_run(
            prompt="prompt 1",
            project_name="proj-1",
            generator_fn=hanging_generator,
        )

        # Same prompt and project should return existing run
        reattached = self.manager.start_run(
            prompt="prompt 1",
            project_name="proj-1",
            generator_fn=hanging_generator,
        )
        self.assertEqual(reattached.run_id, run1.run_id)

        # Different prompt should raise RunAlreadyInProgressError
        with self.assertRaises(RunAlreadyInProgressError):
            self.manager.start_run(
                prompt="prompt 2",
                project_name="proj-2",
                generator_fn=hanging_generator,
            )

        # Clean up hanging task
        run1.task.cancel()
        try:
            await run1.task
        except asyncio.CancelledError:
            pass

    async def test_run_error_handling(self):
        async def failing_generator(prompt, project_name=None):
            yield "Starting...\n"
            await asyncio.sleep(0.01)
            raise RuntimeError("Build error simulated")

        run = self.manager.start_run(
            prompt="failing prompt",
            project_name="fail-proj",
            generator_fn=failing_generator,
        )

        output = []
        async for chunk in self.manager.stream_run(run.run_id):
            output.append(chunk)

        full_output = "".join(output)
        self.assertIn("Starting...", full_output)
        self.assertIn("Execution error: Build error simulated", full_output)
        self.assertEqual(run.status, "error")


class TestActiveRunApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_active_run_api_endpoint(self):
        response = self.client.get("/api/runs/active")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("active", data)
        self.assertIn("status", data)
        self.assertIn("logs", data)
        self.assertIn("run_id", data)

    def test_active_run_stream_404_when_no_run(self):
        from remote_code_agent.services.run_manager import run_manager
        orig_run = run_manager.current_run
        try:
            run_manager.current_run = None
            response = self.client.get("/api/runs/active/stream")
            self.assertEqual(response.status_code, 404)
        finally:
            run_manager.current_run = orig_run


if __name__ == "__main__":
    unittest.main()
