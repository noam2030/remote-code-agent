import os
import unittest
from pathlib import Path


class TestCIWorkflows(unittest.TestCase):
    """Test verification for GitHub Actions CI/CD workflows."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.workflows_dir = self.repo_root / ".github" / "workflows"

    def test_pr_staging_workflow_removed(self):
        """Verify automatic PR staging deployment workflow is removed."""
        pr_staging = self.workflows_dir / "pr-staging.yml"
        self.assertFalse(
            pr_staging.exists(),
            "pr-staging.yml should be removed so staging is not automatically deployed on PRs.",
        )

    def test_pr_verify_workflow_structure(self):
        """Verify pr-verify.yml only runs verification tests."""
        pr_verify = self.workflows_dir / "pr-verify.yml"
        self.assertTrue(pr_verify.exists(), "pr-verify.yml must exist")
        content = pr_verify.read_text()
        self.assertIn("pull_request:", content)
        self.assertIn("branches: [ main ]", content)
        self.assertIn("test-backend:", content)
        self.assertIn("test-frontend:", content)
        self.assertNotIn("deploy-staging:", content)
        self.assertNotIn("gcloud run deploy", content)

    def test_deploy_staging_workflow_structure(self):
        """Verify deploy-staging.yml is triggered via workflow_dispatch."""
        deploy_staging = self.workflows_dir / "deploy-staging.yml"
        self.assertTrue(deploy_staging.exists(), "deploy-staging.yml must exist")
        content = deploy_staging.read_text()
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("deploy_api:", content)
        self.assertIn("deploy_frontend:", content)
        self.assertIn("remote-code-agent-staging", content)
        self.assertIn("npx --yes vercel deploy", content)

    def test_deploy_prod_workflow_structure(self):
        """Verify deploy-prod.yml deploys API to Cloud Run and frontend to Vercel."""
        deploy_prod = self.workflows_dir / "deploy-prod.yml"
        self.assertTrue(deploy_prod.exists(), "deploy-prod.yml must exist")
        content = deploy_prod.read_text()
        self.assertIn("push:", content)
        self.assertIn("branches: [ main ]", content)
        self.assertIn("deploy-api:", content)
        self.assertIn("deploy-frontend:", content)
        self.assertIn("remote-code-agent", content)
        self.assertIn("prj_haBy0oc6TegmML9Z7aj7yKlMFgxm", content)
        self.assertIn("npx --yes vercel deploy --prod", content)


if __name__ == "__main__":
    unittest.main()
