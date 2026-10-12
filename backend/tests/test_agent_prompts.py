"""Unit tests for agent prompts and skills loading from docs/."""

import os
import unittest
from pathlib import Path

from remote_code_agent.services.agent_prompts import (
    find_docs_dir,
    get_agent_system_prompt,
    get_info_retrieval_system_prompt,
    get_prompt_synthesis_system_prompt,
    load_prompt_markdown,
    load_skill,
)


class TestAgentPrompts(unittest.TestCase):
    """Test suite for docs-driven prompt and skill management."""

    def test_find_docs_dir(self):
        """Verifies find_docs_dir locates the existing docs directory."""
        docs_dir = find_docs_dir()
        self.assertTrue(docs_dir.is_dir(), f"Docs dir not found: {docs_dir}")
        self.assertTrue((docs_dir / "prompt.md").is_file(), "prompt.md should exist in docs dir")
        self.assertTrue((docs_dir / "skills").is_dir(), "skills directory should exist in docs dir")

    def test_find_docs_dir_custom_env(self):
        """Verifies find_docs_dir honors custom AGENT_DOCS_DIR environment variable."""
        real_docs = find_docs_dir()
        os.environ["AGENT_DOCS_DIR"] = str(real_docs)
        try:
            detected = find_docs_dir()
            self.assertEqual(detected, real_docs)
        finally:
            os.environ.pop("AGENT_DOCS_DIR", None)

    def test_load_prompt_markdown(self):
        """Verifies loading the raw prompt.md markdown file."""
        content = load_prompt_markdown()
        self.assertIsNotNone(content)
        self.assertIn("# Remote Code Agent - Prompts", content)
        self.assertIn("1. Code Generation Agent Prompt", content)
        self.assertIn("2. Information Retrieval Agent Prompt", content)
        self.assertIn("3. Master Prompt Synthesis Agent Prompt", content)

    def test_load_skill_files(self):
        """Verifies individual skills are loaded from docs/skills/."""
        spec_skill = load_skill("project-specification")
        self.assertIn("project-specification Skill", spec_skill)
        self.assertIn("1. Overview", spec_skill)
        self.assertIn("12. Deployment", spec_skill)

        dev_skill = load_skill("development-workflow")
        self.assertIn("development-workflow Skill", dev_skill)
        self.assertIn("Spec First, Then Code", dev_skill)
        self.assertIn("prompt.txt", dev_skill)

    def test_load_skill_missing(self):
        """Verifies FileNotFoundError is raised when skill file is not on disk."""
        with self.assertRaises(FileNotFoundError):
            load_skill("non-existent-skill")

    def test_get_agent_system_prompt_interpolation(self):
        """Verifies get_agent_system_prompt formats target name and includes discipline rules."""
        prompt = get_agent_system_prompt("my-test-app")
        self.assertIn("building the project 'my-test-app'", prompt)
        self.assertIn("DEVELOPMENT WORKFLOW & SPECIFICATION DISCIPLINE", prompt)
        self.assertIn("project-specification", prompt)
        self.assertIn("development-workflow", prompt)
        self.assertIn("## 1. Overview", prompt)
        self.assertIn("## 12. Deployment", prompt)
        self.assertIn("my-test-app-api", prompt)
        self.assertIn("my-test-app-ui", prompt)
        self.assertIn("ai-learning-499409", prompt)
        self.assertIn("Source type", prompt)
        self.assertIn("PORT is a reserved environment variable", prompt)
        self.assertIn("Google Cloud Firestore", prompt)

    def test_get_info_retrieval_system_prompt_interpolation(self):
        """Verifies get_info_retrieval_system_prompt formats target name and read-only constraints."""
        prompt = get_info_retrieval_system_prompt("analyzer-app")
        self.assertIn("inspecting the project 'analyzer-app'", prompt)
        self.assertIn("CRITICAL CONSTRAINTS", prompt)
        self.assertIn("Do NOT create, write, modify, or delete", prompt)

    def test_get_prompt_synthesis_system_prompt_interpolation(self):
        """Verifies get_prompt_synthesis_system_prompt formats app name and architecture rules."""
        prompt = get_prompt_synthesis_system_prompt("sample-service")
        self.assertIn("Principal Software Architect and Master Prompt Engineer for the project 'sample-service'", prompt)
        self.assertIn("12 mandatory sections", prompt)
        self.assertIn("sample-service-api", prompt)
        self.assertIn("sample-service-ui", prompt)
        self.assertIn("ai-learning-499409", prompt)


if __name__ == "__main__":
    unittest.main()
