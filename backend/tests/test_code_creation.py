import unittest
import os
import sys

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

    def test_agent_config_with_app_name(self):
        test_dir = os.path.join(BASE_WORKSPACE, "test-unit-custom")
        config = get_agent_config(test_dir, app_name="custom-project-name")
        self.assertIn("custom-project-name", config.system_instructions)
        self.assertIn("Google Cloud Run", config.system_instructions)
        self.assertIn("Google Cloud Firestore", config.system_instructions)
        self.assertIn("ai-learning-499409", config.system_instructions)
        self.assertIn("noam-projects2", config.system_instructions)

    def test_code_generator_alias(self):
        self.assertIs(code_generator.generate_code_stream, generate_code_stream)
        self.assertIs(code_generator.create_code_stream, create_code_stream)

    async def test_generate_code_stream_updates_prompt_txt(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_update = AsyncMock()

        class MockAgentCM:
            def __init__(self, config):
                pass
            async def __aenter__(self):
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
                return mock_agent
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("remote_code_agent.services.code_creation.update_project_master_prompt", mock_update), \
             patch("remote_code_agent.services.code_creation.Agent", MockAgentCM), \
             patch("remote_code_agent.services.code_creation.publish_project_to_github", return_value=(True, "https://github.com/test")):

            chunks = []
            async for chunk in generate_code_stream("Build a weather app", project_name="weather-test"):
                chunks.append(chunk)

            mock_update.assert_awaited_once()
            output = "".join(chunks)
            self.assertIn("Consolidating master prompt specification in prompt.txt", output)
            self.assertIn("Master prompt specification updated in prompt.txt", output)
            self.assertIn("Successfully pushed code to GitHub repository", output)

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


if __name__ == "__main__":
    unittest.main()

