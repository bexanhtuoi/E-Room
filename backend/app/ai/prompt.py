import os
from functools import lru_cache

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(AGENT_DIR, "prompts")

DEFAULT_PROMPTS = {
    "main": """You are a helpful assistant with access to a document knowledge base."""
}


def read_prompt_file(agent_name: str) -> str:
    try:
        with open(os.path.join(PROMPTS_DIR, f"{agent_name}.md"), "r", encoding="utf-8") as f:
            return f.read().strip() or DEFAULT_PROMPTS.get(agent_name, "").strip()
    except OSError:
        return DEFAULT_PROMPTS.get(agent_name, "").strip()


load_prompt = lru_cache(maxsize=16)(read_prompt_file)


def get_main_prompt() -> str:
    return load_prompt("main")
