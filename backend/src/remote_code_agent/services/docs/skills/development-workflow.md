# development-workflow Skill

## Discipline: Pair-Programming, Spec-First, Confirmation, Side Branches, PRs, and Testing

### 1. Maintain Prompt History (`prompt.txt`)
- For each project, maintain a `prompt.txt` file located in the project root directory.
- Each user prompt must be appended to this file, separated by a new line.
- For each prompt, prefix a sequential prompt number (e.g., `1. <user prompt>`, `2. <user prompt>`, etc., continuing the sequence if `prompt.txt` already exists).

### 2. Code as a Reflection of the Spec File (`SPEC.md`) - Code as an Exact Reflection of SPEC.md
- The code must always be an exact reflection of the project specification file (`SPEC.md`).
- Every implementation, modification, or bug fix must strictly conform to the architecture, data models, APIs, and requirements defined in `SPEC.md`.
- Never write code or introduce architectural changes that deviate from or contradict `SPEC.md`.

### 3. Requirement Updates (Spec First, Then Code)
- Upon any new prompt that asks to update requirements, add new features, or alter system behavior:
  - **Update the spec first**: First update `SPEC.md` to reflect the new requirements, architecture, data models, or APIs across all 12 mandatory sections.
  - **Then implement according to the spec**: Implement the code changes strictly according to the updated `SPEC.md`.
  - Never write or modify code before the specification is updated to reflect the new requirements.

### 4. Pre-Implementation Confirmation Loop
- Before *any* code change or file modification (excluding the recording of user prompts to `prompt.txt`), the agent must explain in short what it is about to do, summarize the planned changes (including any updates to `SPEC.md` and the codebase), and ask the explicit question: `Confirm?`
- Yield/pause and wait for the user's response.
- Run this alignment loop until the user explicitly confirms (e.g., replies "confirm" or "yes").
- If the user asks clarification questions or asks to implement the change differently:
  - Answer the questions thoroughly.
  - Adapt the plan according to the user's feedback.
  - Summarize the updated plan and ask `Confirm?` again.
  - Yield and repeat until explicit confirmation is received.

### 5. Strict Adherence to the Agreed Implementation
- Once the user confirms, implement the changes *strictly as agreed*: update `SPEC.md` first, then implement the code and automated tests according to the updated specification.
- If an obstacle, error, or limitation arises during implementation that prevents implementing the plan as agreed:
  - **DO NOT** unilaterally implement it in a different way or make unapproved architectural/design deviations.
  - Stop immediately and report the exact issue, explain why the agreed approach cannot proceed as planned, and suggest potential alternatives for the user to review.

### 6. Side Branches & Pull Requests
- Create a dedicated side branch for each feature, refactor, or bug fix (e.g. `feature/<slug>`).
- Commit and push changes to GitHub on the side branch and open a pull request (`gh pr create`).
- Never push directly to `main` for code updates.

### 7. Automated Testing
- Ensure automated tests run on pull requests (e.g., via a GitHub Actions CI workflow or local test execution).
- Pull requests must only be allowed to merge if all automated tests pass cleanly and offline.

### 8. Pull Request Review & Merge Approval
- Do NOT merge the pull request without explicit user approval.
- Present the pull request URL to the user.
- The user will review the pull request and give explicit confirmation (e.g., `merge`) before the pull request can be merged.
- Upon merge confirmation, merge the PR using `gh pr merge --squash --delete-branch` and sync the local workspace with `main`.

### 9. Continuous Deployment Setup
- For each project:
  - Maintain a GitHub Actions workflow that automatically deploys to production on Google Cloud Run (and Vercel for frontend) when code is merged into `main`.
