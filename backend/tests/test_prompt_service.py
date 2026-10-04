import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from remote_code_agent.prompt_service import (
    PROMPT_FILE_NAME,
    extract_baseline_from_readme,
    get_project_prompt_path,
    read_project_prompt,
    synthesize_master_prompt_with_ai,
    synthesize_prompts_fallback,
    update_project_master_prompt,
    write_project_prompt,
)


class TestPromptService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_prompt_service_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_project_prompt_path(self):
        expected = os.path.join(self.test_dir, PROMPT_FILE_NAME)
        self.assertEqual(get_project_prompt_path(self.test_dir), expected)

    def test_read_and_write_project_prompt(self):
        # Missing file returns None
        self.assertIsNone(read_project_prompt(self.test_dir))

        content = "# Master Prompt\n\nBuild a task management app with SQLite."
        write_project_prompt(self.test_dir, content)

        # File exists and matches
        read_back = read_project_prompt(self.test_dir)
        self.assertIsNotNone(read_back)
        self.assertEqual(read_back, content)

        # Whitespace-only file returns None
        prompt_file = get_project_prompt_path(self.test_dir)
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write("   \n\n  ")
        self.assertIsNone(read_project_prompt(self.test_dir))

    def test_extract_baseline_from_readme(self):
        # When README does not exist
        self.assertIsNone(extract_baseline_from_readme(self.test_dir))

        # When README exists
        readme_path = os.path.join(self.test_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "# Currency Converter API\n\n"
                "A fast microservice for real-time exchange rates.\n\n"
                "## Features\n"
                "- Live exchange rate lookup via fixer.io\n"
                "- Caching layer with Redis\n"
            )

        baseline = extract_baseline_from_readme(self.test_dir)
        self.assertIsNotNone(baseline)
        self.assertIn("# Currency Converter API", baseline)
        self.assertIn("Live exchange rate lookup", baseline)

    def test_synthesize_prompts_fallback_initial(self):
        prompt = synthesize_prompts_fallback(
            existing_prompt=None,
            new_prompt="Create a real-time chat application with WebSockets",
            app_name="chat-stream",
        )
        self.assertIn("# Master Project Specification: chat-stream", prompt)
        self.assertIn("Create a real-time chat application with WebSockets", prompt)
        self.assertIn("Google Cloud Run", prompt)

    def test_synthesize_prompts_fallback_incremental(self):
        initial = (
            "# Master Project Specification: chat-stream\n\n"
            "## Overview & Goal\n"
            "Build a chat app.\n\n"
            "## Core Requirements & Features\n"
            "- Create a real-time chat application with WebSockets\n\n"
            "## Technical Guidelines\n"
            "- Cloud Run\n"
        )
        updated = synthesize_prompts_fallback(
            existing_prompt=initial,
            new_prompt="Add dark mode support and user avatars",
            app_name="chat-stream",
        )
        self.assertIn("Create a real-time chat application with WebSockets", updated)
        self.assertIn("- Add dark mode support and user avatars", updated)
        self.assertIn("## Technical Guidelines", updated)

    def test_synthesize_prompts_fallback_deduplication(self):
        existing = (
            "# Master Project Specification: chat-stream\n\n"
            "- Add dark mode support and user avatars\n"
        )
        result = synthesize_prompts_fallback(
            existing_prompt=existing,
            new_prompt="Add dark mode support and user avatars",
            app_name="chat-stream",
        )
        # Should return existing prompt unchanged
        self.assertEqual(result, existing)

    async def test_synthesize_master_prompt_with_ai_mock(self):
        # Mock Agent and response chunks
        mock_chunk = MagicMock()
        mock_chunk.text = (
            "# Consolidated Master Specification: test-app\n\n"
            "Full unified specification covering all requirements seamlessly."
        )

        mock_response = MagicMock()

        async def chunk_generator():
            yield mock_chunk

        mock_response.chunks = chunk_generator()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.chat.return_value = mock_response

        class MockAgentContextManager:
            def __init__(self, config):
                self.config = config

            async def __aenter__(self):
                return mock_agent_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_google_antigravity = MagicMock()
        mock_google_antigravity.Agent = MockAgentContextManager
        mock_google_antigravity.LocalAgentConfig = MagicMock()

        with patch.dict("sys.modules", {"google.antigravity": mock_google_antigravity}):
            result = await synthesize_master_prompt_with_ai(
                existing_prompt="Existing spec",
                new_prompt="New feature request",
                app_name="test-app",
            )
            self.assertIn("Consolidated Master Specification: test-app", result)

    async def test_update_project_master_prompt_e2e(self):
        # Test using deterministic fallback synthesizer to ensure fast, reliable test execution
        with patch(
            "remote_code_agent.services.prompt_service.synthesize_master_prompt_with_ai",
            side_effect=lambda existing, new_p, app: synthesize_prompts_fallback(existing, new_p, app),
        ):
            # 1. Initial prompt creation
            updated = await update_project_master_prompt(
                project_dir=self.test_dir,
                app_name="portfolio-tracker",
                new_prompt="Create a stock portfolio tracking dashboard with charts",
            )
            self.assertIn("portfolio-tracker", updated)
            self.assertIn("Create a stock portfolio tracking dashboard with charts", updated)

            prompt_file = get_project_prompt_path(self.test_dir)
            self.assertTrue(os.path.isfile(prompt_file))

            with open(prompt_file, "r", encoding="utf-8") as f:
                disk_content = f.read()
            self.assertEqual(disk_content.strip(), updated.strip())

            # 2. Incremental prompt update
            updated_2 = await update_project_master_prompt(
                project_dir=self.test_dir,
                app_name="portfolio-tracker",
                new_prompt="Add CSV export and dark theme",
            )
            self.assertIn("Add CSV export and dark theme", updated_2)
            self.assertIn("Create a stock portfolio tracking dashboard with charts", updated_2)


if __name__ == "__main__":
    unittest.main()
