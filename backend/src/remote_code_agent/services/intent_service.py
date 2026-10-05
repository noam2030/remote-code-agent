"""Service for classifying prompt intent (information retrieval vs. code generation/modification)."""

import re
from typing import Optional


# Action verbs that indicate code creation, modification, or project alterations
MUTATION_VERBS = {
    "create",
    "build",
    "make",
    "implement",
    "add",
    "fix",
    "modify",
    "update",
    "refactor",
    "change",
    "delete",
    "remove",
    "replace",
    "write",
    "generate",
    "install",
    "setup",
    "set up",
    "configure",
    "patch",
    "deploy",
    "rewrite",
    "migrate",
    "convert",
    "optimize",
    "enhance",
    "improve",
    "integrate",
    "style",
    "redesign",
    "clean",
}

# Informational / retrieval patterns at beginning of prompt (after polite prefix)
INFO_STARTER_PATTERNS = [
    r"^what\b",
    r"^where\b",
    r"^how\b",
    r"^why\b",
    r"^who\b",
    r"^which\b",
    r"^when\b",
    r"^is\b",
    r"^are\b",
    r"^was\b",
    r"^were\b",
    r"^does\b",
    r"^do\b",
    r"^did\b",
    r"^show(?:\s+me)?\b",
    r"^display\b",
    r"^explain\b",
    r"^describe\b",
    r"^list\b",
    r"^summarize\b",
    r"^summary\b",
    r"^tell\s+me\b",
    r"^inspect\b",
    r"^check\b",
    r"^find\b",
    r"^search\b",
    r"^read\b",
    r"^view\b",
    r"^retrieve\b",
    r"^get\s+(?:info|information|details|status|stats)\b",
    r"^give\s+me\s+(?:an?\s+)?(?:overview|summary|info|details|explanation)\b",
    r"^overview\b",
    r"^status\b",
    r"^diff\b",
]

# Polite prefixes that can be stripped when analyzing command structure
POLITE_PREFIX_PATTERNS = [
    r"^please\s+",
    r"^can\s+you\s+(?:please\s+)?",
    r"^could\s+you\s+(?:please\s+)?",
    r"^would\s+you\s+(?:please\s+)?",
    r"^i\s+(?:just\s+)?(?:want|need|wish)\s+(?:you\s+)?to\s+",
    r"^i\s+would\s+like\s+(?:you\s+)?to\s+",
    r"^kindly\s+",
    r"^help\s+me\s+(?:to\s+)?",
    r"^just\s+",
]

# Secondary mutation conjunctions (e.g. "... and fix it", "... and change it")
MUTATION_CONJUNCTIONS = [
    r"\band\s+(?:also\s+)?(?:fix|change|update|modify|refactor|create|add|implement|delete|remove|rewrite|make)\b",
    r"\bthen\s+(?:fix|change|update|modify|refactor|create|add|implement|delete|remove|rewrite|make)\b",
]


def strip_polite_prefixes(text: str) -> str:
    """Strips conversational polite prefixes from the beginning of a prompt."""
    cleaned = text.strip()
    changed = True
    while changed:
        changed = False
        for pattern in POLITE_PREFIX_PATTERNS:
            new_text = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            if new_text != cleaned:
                cleaned = new_text
                changed = True
                break
    return cleaned


def is_info_retrieval_request(prompt: str) -> bool:
    """Determines whether a user prompt is strictly for retrieving info/inspection.

    Returns True if the prompt is an informational query (read-only), False if it is
    requesting code creation, modification, or project alterations.
    """
    if not prompt or not prompt.strip():
        return True

    raw = prompt.strip()
    clean = raw.lower().lstrip("\"'`# \t\n")

    # If prompt explicitly mentions retrieve info / read only
    if re.search(r"\b(?:retrieve\s+info|only\s+info|read-?only|just\s+info|no\s+code)\b", clean):
        return True

    # Check for chained mutation instructions (e.g., "explain this and fix it")
    for conj_pattern in MUTATION_CONJUNCTIONS:
        if re.search(conj_pattern, clean):
            return False

    # Strip polite prefixes ("please can you...", "i want you to...")
    stripped = strip_polite_prefixes(clean)

    # Check first word of the stripped command
    first_word_match = re.match(r"^([a-z_]+)", stripped)
    first_word = first_word_match.group(1) if first_word_match else ""

    # If the primary action verb is a mutation verb (e.g. "create a...", "add a...", "fix...")
    if first_word in MUTATION_VERBS:
        return False

    # Check if prompt begins with an informational starter
    for pattern in INFO_STARTER_PATTERNS:
        if re.search(pattern, stripped):
            return True

    # If it ends with a question mark and didn't start with a mutation verb
    if raw.endswith("?") and first_word not in MUTATION_VERBS:
        return True

    return False


def detect_project_from_prompt(prompt: str, available_projects: list[str]) -> Optional[str]:
    """Detects if an existing project name is mentioned in the prompt."""
    if not prompt or not available_projects:
        return None

    clean_prompt = prompt.lower()
    for proj in sorted(available_projects, key=len, reverse=True):
        proj_clean = proj.lower()
        pattern = r"(?:\b|_|-)" + re.escape(proj_clean) + r"(?:\b|_|-)"
        if re.search(pattern, clean_prompt) or proj_clean in clean_prompt:
            return proj
    return None
