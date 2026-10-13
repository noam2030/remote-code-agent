import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from remote_code_agent.services.intent_service import (
    detect_project_from_prompt,
    is_confirmation_request,
    is_info_retrieval_request,
    is_merge_request,
    strip_polite_prefixes,
)




class TestIntentService(unittest.TestCase):
    def test_strip_polite_prefixes(self):
        self.assertEqual(strip_polite_prefixes("Please tell me about this"), "tell me about this")
        self.assertEqual(
            strip_polite_prefixes("Can you please explain how auth works?"),
            "explain how auth works?",
        )
        self.assertEqual(
            strip_polite_prefixes("I want you to show me the endpoints"),
            "show me the endpoints",
        )
        self.assertEqual(strip_polite_prefixes("Build a weather app"), "Build a weather app")

    def test_info_retrieval_queries(self):
        queries = [
            "What does this project do?",
            "Where is the database initialized?",
            "How does authentication work?",
            "Why is port 8080 used?",
            "Which endpoints are defined?",
            "Who can access the admin dashboard?",
            "Show me the code in main.py",
            "Show files",
            "List all files in the project",
            "Explain the architecture of this app",
            "Describe the data flow",
            "Summarize the readme",
            "Can you explain how create_user works?",
            "Please show me the test cases",
            "Is Firestore configured for this project?",
            "Are there any unit tests?",
            "Inspect package.json",
            "Check if there are any lint errors",
            "Find where sanitize_project_name is used",
            "Retrieve info about the API structure",
            "Get details on the project schema",
            "Only info: explain what this service is",
        ]
        for q in queries:
            with self.subTest(query=q):
                self.assertTrue(
                    is_info_retrieval_request(q),
                    f"Expected '{q}' to be classified as info retrieval",
                )
    def test_code_mutation_queries(self):
        mutations = [
            "Build a weather app",
            "Create a new endpoint for user login",
            "Add a button to the dashboard",
            "Can you add a button to the dashboard?",
            "Please fix the bug in the auth service",
            "Modify the user schema to include email",
            "Update the README with setup instructions",
            "Refactor project_service.py into smaller modules",
            "Change the primary button color to blue",
            "Delete the old test file",
            "Remove unused imports",
            "Implement password reset with OAuth",
            "Write unit tests for the auth service",
            "Generate a FastAPI CRUD backend",
            "Install tailwindcss and configure it",
            "Set up docker-compose for PostgreSQL",
            "Explain the bug and fix it",
            "Find the endpoint and change it to POST",
        ]
        for m in mutations:
            with self.subTest(mutation=m):
                self.assertFalse(
                    is_info_retrieval_request(m),
                    f"Expected '{m}' to be classified as code mutation",
                )

    def test_detect_project_from_prompt(self):
        projects = ["weather-app", "portfolio-site", "todo-tracker"]
        self.assertEqual(
            detect_project_from_prompt("What does weather-app do?", projects),
            "weather-app",
        )
        self.assertEqual(
            detect_project_from_prompt("Show me files in portfolio-site please", projects),
            "portfolio-site",
        )
        self.assertIsNone(
            detect_project_from_prompt("How does this app work?", projects),
        )

    def test_detect_project_with_spaces_and_separators(self):
        projects = ["hello-world-app", "portfolio-site", "my_custom_tracker"]
        self.assertEqual(
            detect_project_from_prompt("now add very very very small webapplication to serve this hello world app.", projects),
            "hello-world-app",
        )
        self.assertEqual(
            detect_project_from_prompt("update my custom tracker to use postgres", projects),
            "my_custom_tracker",
        )

    def test_confirmation_queries(self):
        confirmations = [
            "confirm",
            "CONFIRM",
            "confirmed",
            "yes",
            "proceed",
            "approved",
            "go ahead",
            "ok",
            "okay",
            "confirm plan",
            "yes, please proceed",
            "please confirm",
            "i confirm",
            "lgtm",
            "looks good",
            "retry",
            "בםמכןרצ",
        ]
        for c in confirmations:
            with self.subTest(query=c):
                self.assertTrue(is_confirmation_request(c), f"Expected '{c}' to be confirmation")
                self.assertFalse(is_info_retrieval_request(c), f"Confirmation '{c}' must not be info retrieval")

    def test_merge_queries(self):
        merges = [
            "merge",
            "MERGE",
            "merge pr",
            "merge pull request",
            "squash and merge",
            "please merge",
            "approve and merge",
            "merge the pr",
        ]
        for m in merges:
            with self.subTest(query=m):
                self.assertTrue(is_merge_request(m), f"Expected '{m}' to be merge request")
                self.assertFalse(is_info_retrieval_request(m), f"Merge '{m}' must not be info retrieval")


if __name__ == "__main__":
    unittest.main()

