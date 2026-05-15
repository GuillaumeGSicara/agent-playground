from functools import cache

from agent_playground.constants import PROMPTS_DIR


@cache
def load_prompt(name: str) -> str:
    """Load a prompt from a .md file in the prompts directory."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
