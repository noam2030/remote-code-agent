import unittest
import os
import sys
import shutil

# Ensure src/ is discoverable even without package installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from google.antigravity import types

from remote_code_agent.code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    get_agent_config,
    get_info_retrieval_agent_config,
    generate_code_stream,
    create_code_stream,
)
import remote_code_agent.code_generator as code_generator
from remote_code_agent.github_service import derive_project_slug


class TestCodeCreation(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        test_dirs = ["test-unit", "test-unit-custom", "test-info-dir", "weather-test", "remote-target-repo"]
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

    def test_agent_config(self):
        test_dir = os.path.join(BASE_WORKSPACE, "test-unit")
        config = get_agent_config(test_dir)
        self.assertIn(test_dir, config.workspaces)
        self.assertIn("Google Cloud Run", config.system_instructions)
        self.assertIn("$PORT", config.system_instructions)
        self.assertIn("Google Cloud Firestore", config.system_instructions)
        self.assertIn("collection", config.system_instructions)
        self.assertIn("Do NOT create virtual environments", config.system_instructions)
        self.assertIn("Do NOT run git or gh commands", config.system_instructions)

        self.assertIn("PORT is a reserved environment variable automatically injected by Cloud Run", config.system_instructions)
        self.assertIn("--port 8080", config.system_instructions)
        self.assertIn("MANDATORY SOURCE TYPE DEPLOYMENT", config.system_instructions)
        self.assertIn("--source .", config.system_instructions)
        self.assertIn("NEVER build docker images locally in GitHub Actions", config.system_instructions)

        # Development workflow and project specification skills
        self.assertIn("development-workflow", config.system_instructions)
        self.assertIn("project-specification", config.system_instructions)
        self.assertIn("SPEC.md", config.system_instructions)
        self.assertIn("## 1. Overview", config.system_instructions)
        self.assertIn("## 12. Deployment", config.system_instructions)
        self.assertIn("Spec First, Then Code", config.system_instructions)
        self.assertIn("Code as an Exact Reflection of SPEC.md", config.system_instructions)

    def test_agent_config_with_app_name(self):
        test_dir = os.path.join(BASE_WORKSPACE, "test-unit-custom")
        config = get_agent_config(test_dir, app_name="custom-project-name")
        self.assertIn("custom-project-name", config.system_instructions)
        self.assertIn("custom-project-name-api", config.system_instructions)
        self.assertIn("custom-project-name-ui", config.system_instructions)
        self.assertIn("Google Cloud Run", config.system_instructions)
        self.assertIn("MANDATORY SOURCE TYPE DEPLOYMENT", config.system_instructions)
        self.assertIn("PORT is a reserved environment variable automatically injected by Cloud Run", config.system_instructions)
        self.assertIn("Google Cloud Firestore", config.system_instructions)
        self.assertIn("ai-learning-499409", config.system_instructions)
        self.assertIn("noam-projects2", config.system_instructions)

        # Development workflow and project specification skills
        self.assertIn("development-workflow", config.system_instructions)
        self.assertIn("project-specification", config.system_instructions)
        self.assertIn("SPEC.md", config.system_instructions)
        self.assertIn("## 1. Overview", config.system_instructions)
        self.assertIn("## 12. Deployment", config.system_instructions)

    def test_code_generator_alias(self):
        self.assertIs(code_generator.generate_code_stream, generate_code_stream)
        self.assertIs(code_generator.create_code_stream, create_code_stream)

    async def test_generate_code_stream_planning_mode(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        class MockAgentCM:
            def __init__(self, config):
                self.config = config
            async def __aenter__(self):
                mock_agent = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.usage_metadata = None
                async def plan_chunks():
                    yield types.Text(step_index=0, text="Here is the planned implementation. Confirm?")
                mock_resp.chunks = plan_chunks()
                mock_agent.chat.return_value = mock_resp
                return mock_agent
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("remote_code_agent.services.code_creation.Agent", MockAgentCM):
            chunks = []
            async for chunk in generate_code_stream("Build a weather app", project_name="weather-test"):
                chunks.append(chunk)

            output = "".join(chunks)
            self.assertIn("Planning Mode", output)
            self.assertIn("Confirm?", output)
            self.assertIn("Dedicated feature branch: 'feature/", output)

    async def test_generate_code_stream_execution_on_confirm(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_update = AsyncMock()
        mock_pr = MagicMock(return_value=(True, "PR created", "https://github.com/testuser/weather-test/pull/1"))
        captured_agent = None

        class MockAgentCM:
            def __init__(self, config):
                pass
            async def __aenter__(self):
                nonlocal captured_agent
                mock_agent = AsyncMock()
                mock_resp = MagicMock()
                mock_meta = MagicMock()
                mock_meta.prompt_token_count = 50
                mock_meta.candidates_token_count = 50
                mock_meta.total_token_count = 100
                mock_resp.usage_metadata = mock_meta
                async def empty_chunks():
                    if False:
                        yield None
                mock_resp.chunks = empty_chunks()
                mock_agent.chat.return_value = mock_resp
                captured_agent = mock_agent
                return mock_agent
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("remote_code_agent.services.code_creation.update_project_master_prompt", mock_update), \
             patch("remote_code_agent.services.code_creation.Agent", MockAgentCM), \
             patch("remote_code_agent.services.code_creation.push_feature_branch_and_create_pr", mock_pr):

            chunks = []
            async for chunk in generate_code_stream("confirm", project_name="weather-test"):
                chunks.append(chunk)

            mock_update.assert_awaited_once()
            mock_pr.assert_called_once()
            output = "".join(chunks)
            self.assertIn("Execution Mode", output)
            self.assertIn("Pull Request Created", output)
            self.assertIn("https://github.com/testuser/weather-test/pull/1", output)
            self.assertIn("Review & Merge Approval", output)

            # Verify agent was invoked with spec-first prompt discipline
            self.assertIsNotNone(captured_agent)
            chat_prompt = captured_agent.chat.call_args[0][0]
            self.assertIn("Spec First, Then Code", chat_prompt)
            self.assertIn("ALL 12 MANDATORY SECTIONS", chat_prompt)
            self.assertIn("Code as a Reflection of the Spec File", chat_prompt)

    async def test_generate_code_stream_merge_mode(self):
        from unittest.mock import MagicMock, patch

        mock_merge = MagicMock(return_value=(True, "Pull Request successfully squash-merged into main"))

        with patch("remote_code_agent.services.code_creation.merge_pull_request", mock_merge):
            chunks = []
            async for chunk in generate_code_stream("merge", project_name="weather-test"):
                chunks.append(chunk)

            mock_merge.assert_called_once()
            output = "".join(chunks)
            self.assertIn("Merge Pull Request", output)
            self.assertIn("Pull Request Merged", output)
            self.assertIn("CI/CD Deployment", output)

    def test_info_retrieval_agent_config(self):
        test_dir = os.path.join(BASE_WORKSPACE, "test-info-dir")
        config = get_info_retrieval_agent_config(test_dir, app_name="test-info-app")
        self.assertIn("test-info-app", config.system_instructions)
        self.assertIn("Do NOT create, write, modify, or delete any files", config.system_instructions)
        self.assertIn("Do NOT write code to disk", config.system_instructions)
        self.assertIn(test_dir, config.workspaces)

    async def test_generate_code_stream_info_retrieval_mode_no_github_publish(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_update = AsyncMock()
        mock_publish = MagicMock(return_value=(True, "https://github.com/test"))

        class MockAgentCM:
            def __init__(self, config):
                self.config = config
            async def __aenter__(self):
                mock_agent = AsyncMock()
                mock_resp = MagicMock()
                mock_meta = MagicMock()
                mock_meta.prompt_token_count = 20
                mock_meta.candidates_token_count = 30
                mock_meta.total_token_count = 50
                mock_resp.usage_metadata = mock_meta
                async def text_chunks():
                    yield types.Text(step_index=0, text="This project is a FastAPI service.")
                mock_resp.chunks = text_chunks()
                mock_agent.chat.return_value = mock_resp
                return mock_agent
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("remote_code_agent.services.code_creation.update_project_master_prompt", mock_update), \
             patch("remote_code_agent.services.code_creation.Agent", MockAgentCM), \
             patch("remote_code_agent.services.code_creation.publish_project_to_github", mock_publish):

            chunks = []
            async for chunk in generate_code_stream("What does this project do?", project_name="weather-test"):
                chunks.append(chunk)

            # Assert prompt.txt is NOT updated during info retrieval
            mock_update.assert_not_called()
            # Assert GitHub publish is NOT called during info retrieval
            mock_publish.assert_not_called()

            output = "".join(chunks)
            self.assertIn("Information Retrieval", output)
            self.assertIn("This project is a FastAPI service.", output)
            self.assertIn("No code changes were made or published to GitHub", output)
            self.assertNotIn("Publishing generated code to project", output)

    async def test_generate_code_stream_syncs_from_github_if_not_local(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_sync = MagicMock(return_value=True)
        mock_update = AsyncMock()
        mock_pr = MagicMock(return_value=(True, "PR created", "https://github.com/noam2030/remote-target-repo/pull/1"))

        class MockAgentCM:
            def __init__(self, config):
                self.config = config
            async def __aenter__(self):
                mock_agent = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.usage_metadata = None
                async def text_chunks():
                    yield types.Text(step_index=0, text="Code implemented.")
                mock_resp.chunks = text_chunks()
                mock_agent.chat.return_value = mock_resp
                return mock_agent
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("remote_code_agent.services.code_creation.sync_project_from_github", mock_sync), \
             patch("remote_code_agent.services.code_creation.update_project_master_prompt", mock_update), \
             patch("remote_code_agent.services.code_creation.Agent", MockAgentCM), \
             patch("remote_code_agent.services.code_creation.push_feature_branch_and_create_pr", mock_pr):

            chunks = []
            async for chunk in generate_code_stream("confirm", project_name="remote-target-repo"):
                chunks.append(chunk)

            output = "".join(chunks)
            mock_sync.assert_called_once()
            mock_pr.assert_called_once()
            self.assertIn("remote-target-repo", output)
            self.assertIn("Cloned repository into workspace from GitHub", output)


if __name__ == "__main__":
    unittest.main()




