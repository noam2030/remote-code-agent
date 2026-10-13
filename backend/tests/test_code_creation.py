import unittest
import os
import sys
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure src/ is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from google.antigravity import types

from remote_code_agent.code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    get_agent_config,
    get_info_retrieval_agent_config,
    execute_agy_cli,
    generate_code_stream,
    create_code_stream,
)
import remote_code_agent.code_generator as code_generator
from remote_code_agent.github_service import derive_project_slug


class TestCodeCreation(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        test_dirs = ["test-unit", "test-unit-custom", "test-info-dir", "weather-test", "remote-target-repo", "hello-test"]
        for d in test_dirs:
            p = os.path.join(BASE_WORKSPACE, d)
            if os.path.exists(p):
                shutil.rmtree(p, ignore_errors=True)

    def test_format_thought_chunk(self):
        chunk = types.Thought(step_index=0, text="Analyzing user requirements")
        result = format_stream_chunk(chunk)
        self.assertEqual(result, "💭 Analyzing user requirements")

    def test_format_text_chunk(self):
        chunk = types.Text(step_index=0, text="Here is the generated code:")
        result = format_stream_chunk(chunk)
        self.assertEqual(result, "Here is the generated code:")

    def test_format_tool_call_chunk(self):
        chunk = types.ToolCall(
            name="write_to_file",
            args={"TargetFile": "/workspace/test-app/main.py", "CodeContent": "print(1)"}
        )
        result = format_stream_chunk(chunk)
        self.assertIn("Tool: write_to_file", result)
        self.assertIn("main.py", result)

    def test_derive_project_slug(self):
        slug = derive_project_slug("Create a web scraper named scraper_pro")
        self.assertTrue(slug.startswith("scraper-pro-"))

    def test_code_generator_alias(self):
        self.assertIs(code_generator.generate_code_stream, generate_code_stream)
        self.assertIs(code_generator.create_code_stream, create_code_stream)

    async def test_execute_agy_cli_success(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Success: Code written and tests pass", b""))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_exec:
            code, stdout, stderr = await execute_agy_cli(
                prompt="Add unit tests",
                project_dir="/workspace/hello-test",
                continue_session=False,
            )

            mock_exec.assert_called_once()
            called_args = mock_exec.call_args[0]
            self.assertIn("-p", called_args)
            self.assertIn("Add unit tests", called_args)
            self.assertIn("--dangerously-skip-permissions", called_args)
            self.assertEqual(mock_exec.call_args[1]["cwd"], "/workspace/hello-test")
            self.assertEqual(code, 0)
            self.assertIn("Success: Code written", stdout)
            self.assertEqual(stderr, "")

    async def test_execute_agy_cli_continue_session(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Resumed session output", b""))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_exec:
            code, stdout, stderr = await execute_agy_cli(
                prompt="confirm",
                project_dir="/workspace/hello-test",
                continue_session=True,
            )

            called_args = mock_exec.call_args[0]
            self.assertIn("--continue", called_args)
            self.assertIn("-p", called_args)
            self.assertEqual(code, 0)
            self.assertEqual(stdout, "Resumed session output")

    async def test_execute_agy_cli_not_found(self):
        with patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError("not found"))):
            code, stdout, stderr = await execute_agy_cli(
                prompt="test",
                project_dir="/workspace/hello-test",
            )
            self.assertEqual(code, 127)
            self.assertIn("not found on system PATH", stderr)

    async def test_generate_code_stream_runs_cli_and_delivers_response(self):
        mock_cli = AsyncMock(return_value=(0, "Implemented FastAPI endpoints for weather service.", ""))

        with patch("remote_code_agent.services.code_creation.execute_agy_cli", mock_cli):
            chunks = []
            async for chunk in generate_code_stream("Build a weather app", project_name="weather-test"):
                chunks.append(chunk)

            mock_cli.assert_called_once()
            self.assertEqual(mock_cli.call_args[1]["prompt"], "Build a weather app")
            self.assertFalse(mock_cli.call_args[1]["continue_session"])

            output = "".join(chunks)
            self.assertIn("Implemented FastAPI endpoints for weather service.", output)
            self.assertIn("Project Stats", output)
            self.assertIn("weather-test", output)

            # Check prompt was appended
            prompt_file = os.path.join(BASE_WORKSPACE, "weather-test", "prompt.txt")
            self.assertTrue(os.path.isfile(prompt_file))
            with open(prompt_file) as f:
                content = f.read()
                self.assertIn("Build a weather app", content)

    async def test_generate_code_stream_merge_mode(self):
        mock_merge = MagicMock(return_value=(True, "Pull Request successfully squash-merged into main"))

        with patch("remote_code_agent.services.code_creation.merge_pull_request", mock_merge):
            chunks = []
            async for chunk in generate_code_stream("merge", project_name="weather-test"):
                chunks.append(chunk)

            mock_merge.assert_called_once()
            output = "".join(chunks)
            self.assertIn("Pull Request Merged", output)
            self.assertIn("CI/CD Deployment", output)

    async def test_generate_code_stream_syncs_from_github_if_not_local(self):
        mock_sync = MagicMock(return_value=True)
        mock_cli = AsyncMock(return_value=(0, "Code implemented.", ""))

        with patch("remote_code_agent.services.code_creation.sync_project_from_github", mock_sync), \
             patch("remote_code_agent.services.code_creation.execute_agy_cli", mock_cli):

            chunks = []
            async for chunk in generate_code_stream("create a hello api", project_name="remote-target-repo"):
                chunks.append(chunk)

            output = "".join(chunks)
            mock_sync.assert_called_once()
            mock_cli.assert_called_once()
    async def test_ensure_agy_oauth_token_writes_file(self):
        from remote_code_agent.core import config
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_home = Path(tmp_dir)
            fake_token_json = '{"token": {"access_token": "fake-token"}}'

            with patch("pathlib.Path.home", return_value=fake_home), \
                 patch.object(config, "AGY_OAUTH_TOKEN", fake_token_json):
                result = config.ensure_agy_oauth_token()
                self.assertTrue(result)
                target_file = fake_home / ".gemini" / "jetski-standalone-oauth-token"
                self.assertTrue(target_file.is_file())
                self.assertEqual(target_file.read_text(encoding="utf-8"), fake_token_json)

    async def test_execute_agy_cli_auth_failure_guidance(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(
            b"",
            b"Authentication required. Please visit the URL to log in: https://accounts.google.com/o/oauth2/auth",
        ))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            code, stdout, stderr = await execute_agy_cli(
                prompt="Implement feature",
                project_dir="/workspace/hello-test",
            )
            self.assertEqual(code, 1)
            self.assertIn("Authentication required", stderr)
            self.assertIn("Authentication Guidance", stderr)
            self.assertIn("AGY_OAUTH_TOKEN", stderr)

    async def test_ensure_agy_settings_creates_settings_file(self):
        from remote_code_agent.core import config
        import tempfile
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_home = Path(tmp_dir)

            with patch("pathlib.Path.home", return_value=fake_home), \
                 patch.object(config, "GEMINI_API_KEY", "test-api-key-123"):
                result = config.ensure_agy_settings()
                self.assertTrue(result)
                settings_file = fake_home / ".gemini" / "antigravity-cli" / "settings.json"
                self.assertTrue(settings_file.is_file())
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                self.assertEqual(data.get("modelProvider"), "gemini")

    async def test_ensure_agy_settings_preserves_existing_keys(self):
        from remote_code_agent.core import config
        import tempfile
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_home = Path(tmp_dir)
            settings_dir = fake_home / ".gemini" / "antigravity-cli"
            settings_dir.mkdir(parents=True, exist_ok=True)
            initial_data = {"trustedWorkspaces": ["/workspace/test"], "permissions": {"allow": ["git"]}}
            (settings_dir / "settings.json").write_text(json.dumps(initial_data), encoding="utf-8")

            with patch("pathlib.Path.home", return_value=fake_home), \
                 patch.object(config, "GEMINI_API_KEY", "test-api-key-123"):
                result = config.ensure_agy_settings()
                self.assertTrue(result)
                data = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
                self.assertEqual(data.get("modelProvider"), "gemini")
                self.assertEqual(data.get("trustedWorkspaces"), ["/workspace/test"])
                self.assertEqual(data.get("permissions"), {"allow": ["git"]})

    async def test_execute_agy_cli_quota_failure_guidance(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 3
        mock_proc.communicate = AsyncMock(return_value=(
            b"",
            b"Error 402, Message: Your prepayment credits are depleted. Status: RESOURCE_EXHAUSTED",
        ))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            code, stdout, stderr = await execute_agy_cli(
                prompt="Implement feature",
                project_dir="/workspace/hello-test",
            )
            self.assertEqual(code, 3)
            self.assertIn("Error 402", stderr)
            self.assertIn("Gemini API Quota Notice", stderr)
            self.assertIn("aistudio.google.com", stderr)


if __name__ == "__main__":
    unittest.main()
