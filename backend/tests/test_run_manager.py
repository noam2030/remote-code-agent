"""Unit tests for RunManager service and cross-device active run streaming."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

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
                if not chunk.startswith(":"):
                    out.append(chunk)
            return "".join(out)

        # Two concurrent listeners (e.g. desktop and mobile)
        res1, res2 = await asyncio.gather(subscriber(), subscriber())
        self.assertEqual(res1, "step_0;step_1;step_2;")
        self.assertEqual(res2, "step_0;step_1;step_2;")

    async def test_stream_heartbeat_keepalive(self):
        async def quiet_generator(prompt, project_name=None):
            yield "Hello"
            await asyncio.sleep(0.06)
            yield "World"

        run = self.manager.start_run(
            prompt="heartbeat test",
            project_name="hb-proj",
            generator_fn=quiet_generator,
        )

        chunks = []
        async for chunk in self.manager.stream_run(run.run_id, heartbeat_interval=0.02):
            chunks.append(chunk)

        self.assertIn(": keepalive\n\n", chunks)
        clean = "".join([c for c in chunks if not c.startswith(":")])
        self.assertEqual(clean, "HelloWorld")


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

    async def test_continuation_run_inherits_prior_logs_on_confirm(self):
        async def plan_gen(prompt, project_name=None):
            yield "📋 Planning feature\nConfirm?\n"

        async def exec_gen(prompt, project_name=None):
            yield "🚀 Executing feature implementation\nPR Created\n"

        # Turn 1: Planning
        run1 = self.manager.start_run(
            prompt="Build weather app",
            project_name="weather-app",
            generator_fn=plan_gen,
        )
        await run1.task

        plan_logs = "".join(run1.logs)
        self.assertEqual(plan_logs, "📋 Planning feature\nConfirm?\n")

        # Turn 2: User confirms
        run2 = self.manager.start_run(
            prompt="confirm",
            project_name="weather-app",
            generator_fn=exec_gen,
        )
        await run2.task

        combined_logs = "".join(run2.logs)
        self.assertIn("📋 Planning feature\nConfirm?\n", combined_logs)
        self.assertIn("💬 [User] confirm", combined_logs)
        self.assertIn("🚀 Executing feature implementation", combined_logs)

        # Streaming with offset matching turn 1 length streams only turn 2 output
        replayed = []
        async for chunk in self.manager.stream_run(run2.run_id, offset=len(plan_logs)):
            replayed.append(chunk)

        turn2_stream = "".join(replayed)
        self.assertNotIn("📋 Planning feature", turn2_stream)
        self.assertIn("💬 [User] confirm", turn2_stream)
        self.assertIn("🚀 Executing feature implementation", turn2_stream)

    async def test_continuation_run_inherits_prior_logs_on_merge(self):
        async def exec_gen(prompt, project_name=None):
            yield "Pull Request created: https://github.com/test/pull/1\n"

        async def merge_gen(prompt, project_name=None):
            yield "🎉 Pull Request Merged!\n"

        # Turn 1: Execution
        run1 = self.manager.start_run(
            prompt="confirm",
            project_name="weather-app",
            generator_fn=exec_gen,
        )
        await run1.task

        # Turn 2: Merge
        run2 = self.manager.start_run(
            prompt="merge",
            project_name="weather-app",
            generator_fn=merge_gen,
        )
        await run2.task

        combined_logs = "".join(run2.logs)
        self.assertIn("Pull Request created", combined_logs)
        self.assertIn("💬 [User] merge", combined_logs)
        self.assertIn("🎉 Pull Request Merged!", combined_logs)

    async def test_arbitrary_followup_prompt_inherits_prior_logs_for_same_project(self):
        async def turn1_gen(prompt, project_name=None):
            yield "Generated component A successfully.\n"

        async def turn2_gen(prompt, project_name=None):
            yield "Publishing code to GitHub repository.\n"

        # Turn 1: implement a
        run1 = self.manager.start_run(
            prompt="implement a",
            project_name="my-app",
            generator_fn=turn1_gen,
        )
        await run1.task

        # Turn 2: arbitrary follow-up (e.g. "great, publish it")
        run2 = self.manager.start_run(
            prompt="great, publish it",
            project_name="my-app",
            generator_fn=turn2_gen,
        )
        await run2.task

        combined_logs = "".join(run2.logs)
        self.assertIn("Generated component A successfully.", combined_logs)
        self.assertIn("💬 [User] great, publish it", combined_logs)
        self.assertIn("Publishing code to GitHub repository.", combined_logs)

    async def test_new_feature_does_not_inherit_prior_logs(self):
        async def gen1(prompt, project_name=None):
            yield "Weather app plan\n"

        async def gen2(prompt, project_name=None):
            yield "Todo app plan\n"

        run1 = self.manager.start_run(
            prompt="Build weather app",
            project_name="weather-app",
            generator_fn=gen1,
        )
        await run1.task

        # New feature prompt should start fresh without inheriting
        run2 = self.manager.start_run(
            prompt="Build todo app",
            project_name="todo-app",
            generator_fn=gen2,
        )
        await run2.task

        combined_logs = "".join(run2.logs)
        self.assertNotIn("Weather app plan", combined_logs)
        self.assertIn("Todo app plan", combined_logs)

    async def test_cancel_run_terminates_task_and_process(self):
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.wait = AsyncMock(return_value=0)

        async def slow_generator(prompt, project_name=None, proc_callback=None):
            if proc_callback:
                proc_callback(mock_proc)
            await asyncio.sleep(5.0)
            yield "never reached"

        run = self.manager.start_run(
            prompt="cancel test",
            project_name="cancel-proj",
            generator_fn=slow_generator,
        )
        await asyncio.sleep(0.01)
        self.assertEqual(run.status, "running")
        self.assertIs(run.process, mock_proc)

        cancelled = await self.manager.cancel_run(run.run_id)
        self.assertTrue(cancelled)
        self.assertEqual(run.status, "cancelled")
        mock_proc.terminate.assert_called_once()
        self.assertIn("Run Cancelled", "".join(run.logs))

        # Trying to cancel again when already cancelled should return False
        again = await self.manager.cancel_run(run.run_id)
        self.assertFalse(again)


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

    def test_cancel_active_run_endpoint(self):
        from remote_code_agent.services.run_manager import run_manager, ActiveRun
        run = ActiveRun(
            run_id="test-cancel-id",
            project_name="test-proj",
            prompt="test prompt",
            status="running",
            started_at=time.time(),
        )
        orig_run = run_manager.current_run
        run_manager.current_run = run
        try:
            res = self.client.post("/api/runs/cancel")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "cancelled")
        finally:
            run_manager.current_run = orig_run

    def test_cancel_run_by_id_endpoint(self):
        from remote_code_agent.services.run_manager import run_manager, ActiveRun
        run = ActiveRun(
            run_id="test-cancel-id-2",
            project_name="test-proj",
            prompt="test prompt",
            status="running",
            started_at=time.time(),
        )
        orig_run = run_manager.current_run
        run_manager.current_run = run
        try:
            res = self.client.post("/api/runs/test-cancel-id-2/cancel")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "cancelled")
        finally:
            run_manager.current_run = orig_run

    def test_cancel_run_400_when_no_active_run(self):
        from remote_code_agent.services.run_manager import run_manager
        orig_run = run_manager.current_run
        try:
            run_manager.current_run = None
            res = self.client.post("/api/runs/cancel")
            self.assertEqual(res.status_code, 400)
        finally:
            run_manager.current_run = orig_run


if __name__ == "__main__":
    unittest.main()
