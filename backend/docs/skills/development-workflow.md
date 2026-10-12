# development-workflow Skill

## Discipline: Spec-First, Testing, and Prompt History

### 1. SPEC FIRST: Spec First, Then Code
- When creating or updating an application, you MUST create or update `SPEC.md` FIRST before implementing code changes.
- Never write code or modify implementation files before the specification is updated to reflect the new requirements.

### 2. CODE AS REFLECTION OF SPEC: Code as an Exact Reflection of SPEC.md
- Every implementation, modification, or bug fix must strictly conform to `SPEC.md`.
- Never write code or introduce architectural changes that deviate from or contradict `SPEC.md`.

### 3. Prompt History (prompt.txt)
- Maintain and preserve a `prompt.txt` file located in the project root directory.
- Record sequential user prompts in `prompt.txt` (e.g., `1. <prompt>`, `2. <prompt>`).

### 4. Automated Testing
- Always include comprehensive automated tests in a `tests/` directory validating full functionality.
- Ensure high test coverage and regression-free updates.
- Tests must pass cleanly and offline without requiring active external cloud dependencies (using mocks or in-memory fallbacks).
