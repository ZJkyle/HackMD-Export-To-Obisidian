"""Configuration system for notetrans."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("~/.config/notetrans/config.yaml").expanduser()

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "organizer": {
        "rules": [
            {
                "name": "thesis",
                "destination": "1-Projects/thesis",
                "keywords": [
                    "Proposal", "Paper Writing", "Proposed method",
                    "\u53e3\u8a66", "\u7562\u696d", "\u78a9\u4e8c\u54aa", "\u78a9\u535a", "\u570b\u79d1\u6703",
                ],
                "case_sensitive": False,
            },
            {
                "name": "mypda",
                "destination": "1-Projects/mypda",
                "keywords": ["myPDA", "mypda", "MyPDA"],
                "case_sensitive": True,
            },
            {
                "name": "client-work",
                "destination": "1-Projects/client-work",
                "keywords": [
                    "BankChat", "Bankchat", "PoliceChat", "Policechat",
                    "\u74db\u8072", "\u5c0a\u535a", "\u5168\u8208",
                ],
                "case_sensitive": True,
            },
            {
                "name": "meetings",
                "destination": "4-Archive/meetings",
                "keywords": [
                    "Progress Meeting", "Progress meeting", "\u9032\u5ea6\u54aa",
                    "Scalable meeting", "BD \u4f8b\u6703", "Meet with",
                    "Meet w", "\u6703\u8b70\u7d00\u9304", "\u6703\u8b70\u8a18\u9304",
                ],
                "case_sensitive": False,
            },
            {
                "name": "papers",
                "destination": "3-Resources/papers",
                "match_type": "paper_note",
            },
            {
                "name": "courses",
                "destination": "3-Resources/courses",
                "keywords": [
                    "Assignment", "Homework", "HW", "Lab ",
                    "ICLAB", "VLSI", "Algorithm", "\u5bc6\u78bc\u5de5\u7a0b",
                    "\u751f\u91ab\u96fb\u5b50", "ACAL", "Arch", "DIC",
                    "\u671f\u4e2d\u8003", "\u671f\u672b", "C++ \u5b78\u7fd2",
                ],
                "case_sensitive": False,
            },
            {
                "name": "tech",
                "destination": "3-Resources/tech",
                "keywords": [
                    "llama.cpp", "Llama.cpp", "Docker", "Raspberry",
                    "Rapsberry", "Setup", "Server", "Cluster",
                    "Cross Compile", "AIAS", "Jetson",
                    "Environment",
                ],
                "case_sensitive": False,
            },
            {
                "name": "career",
                "destination": "2-Areas/career",
                "keywords": ["Interview", "\u9762\u8a66", "TSMC"],
                "case_sensitive": False,
            },
            {
                "name": "research",
                "destination": "2-Areas/research",
                "keywords": [
                    "KV Cache", "Softmax", "MoA", "MOE", "MoE",
                    "Flash attention", "Splitwise", "StreamLLM",
                    "inference optimization", "Efficient KV",
                    "eviction", "hallucination", "Data distillation",
                    "Data Gen", "Experiment",
                ],
                "case_sensitive": False,
            },
            {
                "name": "journal",
                "destination": "4-Archive/journal",
                "keywords": [
                    "\u4eca\u65e5", "\u6bcf\u65e5", "\u6392\u7a0b", "\u5de5\u4f5c\u8868", "Time Table",
                    "\u505a\u5b8c\u7684\u4e8b",
                ],
                "case_sensitive": False,
            },
            {
                "name": "personal",
                "destination": "4-Archive/personal",
                "keywords": [
                    "\u70e4\u8089", "Happy New Year", "first song",
                    "Distance of Blue", "Video making",
                    "image",
                ],
                "case_sensitive": False,
            },
        ],
        "topics": [
            {"pattern": "llama.cpp", "tag": "topic/llama-cpp"},
            {"pattern": "kv cache", "tag": "topic/kv-cache"},
            {"pattern": "kv-cache", "tag": "topic/kv-cache"},
            {"pattern": "mixture of agents", "tag": "topic/moa"},
            {"pattern": "moa", "tag": "topic/moa"},
            {"pattern": "mixture of experts", "tag": "topic/moe"},
            {"pattern": "moe", "tag": "topic/moe"},
            {"pattern": "softmax", "tag": "topic/llm-inference"},
            {"pattern": "flash attention", "tag": "topic/llm-inference"},
            {"pattern": "bankchat", "tag": "topic/classifier"},
            {"pattern": "policechat", "tag": "topic/classifier"},
            {"pattern": "mypda", "tag": "topic/mypda"},
            {"pattern": "cryptography", "tag": "topic/cryptography"},
            {"pattern": "vlsi", "tag": "topic/vlsi"},
            {"pattern": "iclab", "tag": "topic/iclab"},
            {"pattern": "algorithm", "tag": "topic/algorithm"},
        ],
        "folder_tags": {
            "4-Archive/meetings": "type/meeting",
            "3-Resources/papers": "type/paper",
            "3-Resources/courses": "type/assignment",
            "3-Resources/tech": "type/howto",
            "1-Projects/thesis": "project/thesis",
            "1-Projects/mypda": "project/mypda",
            "1-Projects/client-work": "project/thesis",
        },
        "delete_empty": True,
        "empty_min_chars": 10,
        "untitled_min_chars": 100,
        "inbox_folder": "0-Inbox",
    },
    "extractor": {
        "api_base": "http://localhost:8000/v1",
        "model": "Qwen/Qwen3-VL-8B-Instruct-FP8",
        "temperature": 0.3,
        "max_tokens": 4096,
        "prompt_language": "zh",
        "output_dir": "2-Areas/research",
        "delay": 1.0,
    },
}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPTS = {
    "zh": """\
\u4f60\u662f\u4e00\u4f4d\u77e5\u8b58\u7ba1\u7406\u52a9\u624b\u3002\u8acb\u95b1\u8b80\u4ee5\u4e0b\u6703\u8b70\u7d00\u9304/\u7b46\u8a18\uff0c\u63d0\u53d6\u5176\u4e2d\u503c\u5f97\u9577\u671f\u4fdd\u5b58\u7684\u6838\u5fc3\u77e5\u8b58\u9ede\u3002

\u5c0d\u6bcf\u500b\u77e5\u8b58\u9ede\uff0c\u8f38\u51fa\u4e00\u500b JSON \u7269\u4ef6\uff1a
- title: \u7c21\u77ed\u6a19\u984c\uff08\u4e2d\u82f1\u7686\u53ef\uff09
- tags: \u5efa\u8b70\u7684\u6a19\u7c64\u5217\u8868
- content: \u7528 Markdown \u683c\u5f0f\u5beb\u51fa\u5b8c\u6574\u7684\u6c38\u4e45\u7b46\u8a18\uff0c\u5305\u542b\uff1a
  - \u6838\u5fc3\u89c0\u9ede\uff08\u4e00\u5169\u53e5\u8a71\uff09
  - \u7d30\u7bc0\u8aaa\u660e
  - \u4f86\u6e90\u5f15\u7528\uff08\u539f\u7b46\u8a18\u6a19\u984c\uff09

\u5982\u679c\u7b46\u8a18\u6c92\u6709\u503c\u5f97\u63d0\u53d6\u7684\u77e5\u8b58\u9ede\uff0c\u56de\u50b3\u7a7a\u9663\u5217\u3002
\u8f38\u51fa\u683c\u5f0f\uff1aJSON array\uff0c\u4e0d\u8981\u591a\u9918\u6587\u5b57\u3002

---

\u7b46\u8a18\u6a19\u984c\uff1a{title}

{content}""",
    "en": """\
You are a knowledge management assistant. Read the following meeting notes/log \
and extract core knowledge points worth preserving long-term.

For each knowledge point, output a JSON object:
- title: A short title
- tags: A list of suggested tags
- content: A complete permanent note in Markdown format, including:
  - Core insight (one or two sentences)
  - Detailed explanation
  - Source reference (original note title)

If the note has no knowledge points worth extracting, return an empty array.
Output format: JSON array, no extra text.

---

Note title: {title}

{content}""",
}


# ---------------------------------------------------------------------------
# Loading / merging
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*.

    Lists and non-dict values in *override* replace those in *base*.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from a YAML file, merged with defaults.

    Parameters
    ----------
    path:
        Path to YAML config file.  If *None*, uses ``DEFAULT_CONFIG_PATH``
        but does **not** error if the file is missing (returns pure defaults).

    Returns
    -------
    dict
        Merged configuration dictionary.
    """
    if path is not None:
        config_path = Path(path).expanduser()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, encoding="utf-8") as fh:
            user_config = yaml.safe_load(fh) or {}
        return _deep_merge(DEFAULT_CONFIG, user_config)

    # Default path: load if exists, otherwise return defaults
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as fh:
            user_config = yaml.safe_load(fh) or {}
        return _deep_merge(DEFAULT_CONFIG, user_config)

    return copy.deepcopy(DEFAULT_CONFIG)


def generate_default_config() -> str:
    """Return the default configuration as a YAML string."""
    return yaml.dump(
        DEFAULT_CONFIG,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )


def get_prompt(language: str = "zh") -> str:
    """Return the extraction prompt template for the given language."""
    return PROMPTS.get(language, PROMPTS["zh"])
