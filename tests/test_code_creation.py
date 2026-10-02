import unittest
import os
from google.antigravity import types

from code_creation import (
    BASE_WORKSPACE,
    format_stream_chunk,
    get_agent_config,
    generate_code_stream,
    create_code_stream,
)
import code_generator
from github_service import derive_project_slug


class TestCodeCreation(unittest.TestCase):
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

    def test_code_generator_alias(self):
        self.assertIs(code_generator.generate_code_stream, generate_code_stream)
        self.assertIs(code_generator.create_code_stream, create_code_stream)


if __name__ == "__main__":
    unittest.main()
