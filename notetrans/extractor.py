"""Extract Zettelkasten permanent notes from meeting/experiment logs via LLM."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from notetrans.config import DEFAULT_CONFIG, get_prompt, load_config
from notetrans.organizer import read_frontmatter, write_frontmatter


# ---------------------------------------------------------------------------
# Legacy constants (kept for backward compatibility)
# ---------------------------------------------------------------------------

DEFAULT_LLM_URL = "http://localhost:8000/v1"
DEFAULT_LLM_MODEL = "Qwen/Qwen3-VL-8B-Instruct-FP8"

EXTRACT_PROMPT = get_prompt("zh")

# Destination for generated zettel notes
ZETTEL_DEST = "2-Areas/research"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class ZettelNote:
    title: str
    tags: list[str] = field(default_factory=list)
    content: str = ""
    source_title: str = ""


@dataclass
class ExtractStats:
    notes_scanned: int = 0
    zettels_created: int = 0
    errors: int = 0


# ---------------------------------------------------------------------------
# LLM Client (using requests to keep dependencies minimal)
# ---------------------------------------------------------------------------

def _call_llm(
    prompt: str,
    *,
    llm_url: str = DEFAULT_LLM_URL,
    llm_api_key: str = "",
    llm_model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Call OpenAI-compatible chat completion API."""
    import requests

    url = f"{llm_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if llm_api_key:
        headers["Authorization"] = f"Bearer {llm_api_key}"

    payload = {
        "model": llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# JSON Parsing
# ---------------------------------------------------------------------------

def _parse_zettel_json(raw: str) -> list[dict]:
    """Parse LLM output as JSON array, tolerating markdown code fences."""
    text = raw.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        # Remove first line (```json or ```) and last line (```)
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Handle <think>...</think> blocks from Qwen
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Zettel file generation
# ---------------------------------------------------------------------------

def _generate_zettel_md(zettel: ZettelNote) -> str:
    """Generate a markdown file with frontmatter for a zettel note."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = {
        "title": zettel.title,
        "created": now,
        "tags": zettel.tags,
        "source": f"[[{zettel.source_title}]]",
    }
    dumped = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    body = f"# {zettel.title}\n\n{zettel.content}\n\n## Source\n- [[{zettel.source_title}]]\n"
    return f"---\n{dumped}---\n\n{body}"


def _sanitize_filename(title: str) -> str:
    """Create a safe filename from a zettel title."""
    name = title.strip()
    if not name:
        name = "Untitled Zettel"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 200:
        name = name[:200]
    return name


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_zettels(
    vault_dir: Path,
    *,
    source_dir: str = "4-Archive/meetings",
    llm_url: str = DEFAULT_LLM_URL,
    llm_api_key: str = "",
    llm_model: str = DEFAULT_LLM_MODEL,
    dry_run: bool = False,
    delay: float = 0.5,
    config: dict[str, Any] | None = None,
) -> tuple[list[ZettelNote], ExtractStats]:
    """Scan source_dir for .md files, extract zettel notes via LLM.

    Parameters
    ----------
    config:
        Full configuration dict.  If provided, its ``extractor`` section
        supplies defaults for *llm_url*, *llm_model*, etc.  Explicit
        keyword arguments still take priority when they differ from the
        function-signature defaults.

    Returns (zettels, stats).
    """
    # Resolve settings: explicit kwargs > config > built-in defaults
    ext_cfg: dict[str, Any] = {}
    if config is not None:
        ext_cfg = config.get("extractor", {})

    effective_url = llm_url if llm_url != DEFAULT_LLM_URL else ext_cfg.get("api_base", DEFAULT_LLM_URL)
    effective_model = llm_model if llm_model != DEFAULT_LLM_MODEL else ext_cfg.get("model", DEFAULT_LLM_MODEL)
    effective_temperature = ext_cfg.get("temperature", 0.3)
    effective_max_tokens = ext_cfg.get("max_tokens", 4096)
    effective_output_dir = ext_cfg.get("output_dir", ZETTEL_DEST)
    effective_delay = delay if delay != 0.5 else ext_cfg.get("delay", 0.5)
    prompt_language = ext_cfg.get("prompt_language", "zh")
    prompt_template = get_prompt(prompt_language)

    src = vault_dir / source_dir
    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    md_files = sorted(src.glob("*.md"))
    stats = ExtractStats(notes_scanned=len(md_files))
    all_zettels: list[ZettelNote] = []

    dest_dir = vault_dir / effective_output_dir
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    for filepath in md_files:
        fm, body = read_frontmatter(filepath)
        title = fm.get("title", filepath.stem) or filepath.stem
        content = body.strip()

        # Skip very short notes
        if len(content) < 50:
            continue

        # Build prompt
        prompt = prompt_template.format(title=title, content=content[:6000])

        try:
            raw = _call_llm(
                prompt,
                llm_url=effective_url,
                llm_api_key=llm_api_key,
                llm_model=effective_model,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
            )
        except Exception:
            stats.errors += 1
            continue

        parsed = _parse_zettel_json(raw)

        for item in parsed:
            zettel = ZettelNote(
                title=item.get("title", "Untitled"),
                tags=item.get("tags", []),
                content=item.get("content", ""),
                source_title=title,
            )
            all_zettels.append(zettel)

            if not dry_run:
                md_content = _generate_zettel_md(zettel)
                fname = _sanitize_filename(zettel.title) + ".md"
                dest_path = dest_dir / fname
                # Avoid overwriting
                if dest_path.exists():
                    counter = 1
                    stem = _sanitize_filename(zettel.title)
                    while dest_path.exists():
                        dest_path = dest_dir / f"{stem} ({counter}).md"
                        counter += 1
                dest_path.write_text(md_content, encoding="utf-8")
                stats.zettels_created += 1

        if effective_delay > 0:
            time.sleep(effective_delay)

    return all_zettels, stats
