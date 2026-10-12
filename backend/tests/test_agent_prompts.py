"""Unit tests for agent prompts and dynamic skills loading from GitHub."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from remote_code_agent.services.agent_prompts import (
    clear_loaded_skills,
    find_docs_dir,
    get_agent_system_prompt,
    get_combined_skills,
    get_info_retrieval_system_prompt,
    get_loaded_skills,
    get_prompt_synthesis_system_prompt,
    get_user_chat_prompt,
    load_dynamic_skills,
    load_prompt_markdown,
    load_skill,
    parse_github_tree_url,
    set_loaded_skills,
)


class TestAgentPrompts(unittest.TestCase):
    """Test suite for docs-driven prompt and dynamic skills management."""

    def setUp(self):
        # Reset skills cache before each test
        load_dynamic_skills(force_refresh=True)

    def test_find_docs_dir(self):
        """Verifies find_docs_dir locates the existing docs directory."""
        docs_dir = find_docs_dir()
        self.assertTrue(docs_dir.is_dir(), f"Docs dir not found: {docs_dir}")
        self.assertTrue((docs_dir / "prompt.md").is_file(), "prompt.md should exist in docs dir")

    def test_skills_not_in_project_files(self):
        """Verifies that skills are NOT stored as static files in the project workspace, and no fallback constants exist."""
        docs_dir = find_docs_dir()
        self.assertFalse(
            (docs_dir / "skills").exists(),
            "skills directory must not exist in project files (must be loaded dynamically)",
        )
        import remote_code_agent.services.agent_prompts as ap
        import remote_code_agent.core.config as cfg
        self.assertFalse(hasattr(ap, "FALLBACK_SKILLS"), "FALLBACK_SKILLS must not exist")
        self.assertFalse(hasattr(cfg, "DEFAULT_SKILLS_REPO_URL"), "DEFAULT_SKILLS_REPO_URL must not exist")

    def test_parse_github_tree_url(self):
        """Verifies parsing of the remote GitHub skills repository URL."""
        url = "https://github.com/noam2030/build-with-agent/tree/main/.agents/skills"
        parsed = parse_github_tree_url(url)
        self.assertEqual(parsed["owner"], "noam2030")
        self.assertEqual(parsed["repo"], "build-with-agent")
        self.assertEqual(parsed["branch"], "main")
        self.assertEqual(parsed["path"], ".agents/skills")

        # Also test bare repo URL fallback
        bare = parse_github_tree_url("https://github.com/noam2030/build-with-agent")
        self.assertEqual(bare["owner"], "noam2030")
        self.assertEqual(bare["repo"], "build-with-agent")
        self.assertEqual(bare["branch"], "main")
        self.assertEqual(bare["path"], "")

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

    def test_load_skill_dynamic(self):
        """Verifies individual skills are loaded dynamically."""
        spec_skill = load_skill("project-specification")
        self.assertIn("project-specification", spec_skill)
        self.assertIn("1. Overview", spec_skill)
        self.assertIn("12. Deployment", spec_skill)

        dev_skill = load_skill("development-workflow")
        self.assertIn("development-workflow", dev_skill)
        self.assertIn("Spec First, Then Code", dev_skill)
        self.assertIn("prompt.txt", dev_skill)

    def test_load_skill_missing(self):
        """Verifies FileNotFoundError is raised when skill is not found."""
        with self.assertRaises(FileNotFoundError):
            load_skill("non-existent-skill")

    def test_set_and_get_loaded_skills(self):
        """Verifies programmatic manipulation and retrieval of loaded skills."""
        custom_skills = {
            "custom-skill": "### Custom Skill Instructions",
            "project-specification": "# Custom Spec",
        }
        set_loaded_skills(custom_skills)
        loaded = get_loaded_skills()
        self.assertIn("custom-skill", loaded)
        self.assertEqual(load_skill("custom-skill"), "### Custom Skill Instructions")

    def test_clear_loaded_skills_reloads_on_demand(self):
        """Verifies clear_loaded_skills clears cache and get_loaded_skills re-loads."""
        clear_loaded_skills()
        loaded = get_loaded_skills()
        self.assertTrue(len(loaded) > 0)
        self.assertIn("project-specification", loaded)

    @patch("remote_code_agent.services.agent_prompts.fetch_remote_skills")
    def test_load_dynamic_skills_network_error_handled(self, mock_fetch):
        """Verifies network exceptions during remote fetch are handled and return empty dict without crashing."""
        mock_fetch.side_effect = Exception("Simulated network failure")
        clear_loaded_skills()
        skills = load_dynamic_skills(force_refresh=True)
        self.assertEqual(skills, {})
        with self.assertRaises(FileNotFoundError):
            load_skill("project-specification")

    def test_get_combined_skills(self):
        """Verifies get_combined_skills orders core skills first and formats output."""
        combined = get_combined_skills()
        self.assertIn("project-specification", combined)
        self.assertIn("development-workflow", combined)

    def test_get_agent_system_prompt_interpolation(self):
        """Verifies get_agent_system_prompt formats target name and includes discipline rules."""
        prompt = get_agent_system_prompt("my-test-app")
        self.assertIn("building the project 'my-test-app'", prompt)
        self.assertIn("DEVELOPMENT WORKFLOW & SPECIFICATION DISCIPLINE", prompt)
        self.assertIn("project-specification", prompt)
        self.assertIn("development-workflow", prompt)
        self.assertIn("1. Overview", prompt)
        self.assertIn("12. Deployment", prompt)
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

    def test_get_user_chat_prompt_interpolation(self):
        """Verifies get_user_chat_prompt formats app name, user instruction, and skills."""
        prompt = get_user_chat_prompt("chat-app", "Build a hello world web UI")
        self.assertIn("building the project 'chat-app'", prompt)
        self.assertIn("MANDATORY DEVELOPMENT WORKFLOW & SPECIFICATION DISCIPLINE", prompt)
        self.assertIn("project-specification", prompt)
        self.assertIn("development-workflow", prompt)
        self.assertIn("chat-app-api", prompt)
        self.assertIn("chat-app-ui", prompt)
        self.assertIn("Build a hello world web UI", prompt)


if __name__ == "__main__":
    unittest.main()
