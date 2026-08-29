import os
from functools import lru_cache

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(AGENT_DIR, "prompts")

DEFAULT_PROMPTS = {
    "main": """You are a helpful assistant with access to a document knowledge base."""
}

@lru_cache(maxsize=16)
def load_prompt_from_file(agent_name: str) -> str:
    file_path = os.path.join(PROMPTS_DIR, f"{agent_name}.md")

    try:
        if not os.path.exists(file_path):
            return DEFAULT_PROMPTS.get(agent_name, "").strip()

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return DEFAULT_PROMPTS.get(agent_name, "").strip()
            return content

    except Exception:
        return DEFAULT_PROMPTS.get(agent_name, "").strip()


def get_main_prompt() -> str:
    return load_prompt_from_file("main")

