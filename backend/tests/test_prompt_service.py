import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from remote_code_agent.prompt_service import (
    PROMPT_FILE_NAME,
    append_numbered_prompt,
    extract_baseline_from_readme,
    get_last_feature_prompt,
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
        self.assertIn("Firestore", prompt)
        self.assertIn("chat-stream", prompt)
        self.assertIn("never pass PORT in --set-env-vars", prompt)
        self.assertIn("--port 8080", prompt)
        self.assertIn("MUST use Source type", prompt)
        self.assertIn("--source .", prompt)
        self.assertIn("do NOT use docker build/push", prompt)
        self.assertIn("SPEC.md", prompt)
        self.assertIn("all 12 mandatory sections", prompt)
        self.assertIn("Spec-First", prompt)

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
            config_call = mock_google_antigravity.LocalAgentConfig.call_args
            self.assertIn("SPEC.md", config_call.kwargs["system_instructions"])
            self.assertIn("12 mandatory sections", config_call.kwargs["system_instructions"])

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

    def test_append_numbered_prompt_and_get_last_feature(self):
        num1 = append_numbered_prompt(self.test_dir, "Build a weather forecast dashboard")
        self.assertEqual(num1, 1)

        num2 = append_numbered_prompt(self.test_dir, "confirm")
        self.assertEqual(num2, 2)

        num3 = append_numbered_prompt(self.test_dir, "confrim")
        self.assertEqual(num3, 3)

        num4 = append_numbered_prompt(self.test_dir, "confirm plan")
        self.assertEqual(num4, 4)

        # get_last_feature_prompt skips all confirmations and returns the original instruction
        last_feat = get_last_feature_prompt(self.test_dir)
        self.assertEqual(last_feat, "Build a weather forecast dashboard")

        num5 = append_numbered_prompt(self.test_dir, "merge")
        self.assertEqual(num5, 5)

        last_feat_after_merge = get_last_feature_prompt(self.test_dir)
        self.assertEqual(last_feat_after_merge, "Build a weather forecast dashboard")

        # Adding a new feature prompt updates the last feature
        num6 = append_numbered_prompt(self.test_dir, "Add temperature toggle between C and F")
        self.assertEqual(num6, 6)

        last_feat_new = get_last_feature_prompt(self.test_dir)
        self.assertEqual(last_feat_new, "Add temperature toggle between C and F")


if __name__ == "__main__":
    unittest.main()
