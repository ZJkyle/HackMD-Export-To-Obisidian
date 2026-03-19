"""Organize vault notes into PARA + Zettelkasten folder structure."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from notetrans.config import DEFAULT_CONFIG, load_config


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def read_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Read YAML frontmatter and body from a markdown file.

    Returns (frontmatter_dict, body_str). If no frontmatter found,
    returns ({}, full_content).
    """
    text = filepath.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_str = text[3:end]
            body = text[end + 3:].lstrip("\n")
            try:
                fm = yaml.safe_load(fm_str) or {}
            except yaml.YAMLError:
                fm = {}
            return fm, body
    return {}, text


def write_frontmatter(filepath: Path, fm: dict, body: str) -> None:
    """Write markdown file with YAML frontmatter + body."""
    dumped = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    filepath.write_text(f"---\n{dumped}---\n\n{body}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

DELETE = "__DELETE__"


@dataclass
class ClassifyResult:
    filepath: Path
    dest_folder: str  # relative to vault root, or DELETE
    tags_to_add: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Matcher helpers
# ---------------------------------------------------------------------------

def _is_empty_or_untitled(
    filepath: Path,
    title: str,
    content: str,
    *,
    empty_min_chars: int = 10,
    untitled_min_chars: int = 100,
) -> bool:
    """Note is empty, nearly empty, or has no meaningful title."""
    body = content.strip()
    # Truly empty or only whitespace
    if len(body) < empty_min_chars:
        return True
    # Title is missing or generic "Untitled"
    if not title or title.strip().lower() == "untitled":
        # But if body has substantial content, keep it
        if len(body) > untitled_min_chars:
            return False
        return True
    return False


def _matches_any(patterns: list[str], text: str, *, case_sensitive: bool = False) -> bool:
    """Check if any pattern appears in text."""
    if case_sensitive:
        for p in patterns:
            if p in text:
                return True
    else:
        text_lower = text.lower()
        for p in patterns:
            if p.lower() in text_lower:
                return True
    return False


def _is_paper_note(title: str, content: str) -> bool:
    """Detect paper reading notes: mostly uppercase title or paper keywords."""
    # Titles that are mostly uppercase words (paper titles)
    words = title.split()
    if len(words) >= 4:
        upper_count = sum(1 for w in words if w[0:1].isupper())
        if upper_count / len(words) >= 0.8:
            # Also check content for paper-related keywords
            if _matches_any(["abstract", "arxiv", "paper", "authors",
                             "contribution", "method", "approach"], content):
                return True
    # Direct keyword match
    if _matches_any(["paper reading", "paper review", "paper notes",
                     "literature review"], title):
        return True
    return False


# ---------------------------------------------------------------------------
# Topic tag scanning
# ---------------------------------------------------------------------------

# Legacy module-level constants kept for backward compatibility
TOPIC_PATTERNS: list[tuple[str, str]] = [
    ("llama.cpp", "topic/llama-cpp"),
    ("kv cache", "topic/kv-cache"),
    ("kv-cache", "topic/kv-cache"),
    ("mixture of agents", "topic/moa"),
    ("moa", "topic/moa"),
    ("mixture of experts", "topic/moe"),
    ("moe", "topic/moe"),
    ("softmax", "topic/llm-inference"),
    ("flash attention", "topic/llm-inference"),
    ("bankchat", "topic/classifier"),
    ("policechat", "topic/classifier"),
    ("mypda", "topic/mypda"),
    ("cryptography", "topic/cryptography"),
    ("vlsi", "topic/vlsi"),
    ("iclab", "topic/iclab"),
    ("algorithm", "topic/algorithm"),
]

# Folder -> type tag mapping
FOLDER_TAG_MAP: dict[str, str] = {
    "4-Archive/meetings": "type/meeting",
    "3-Resources/papers": "type/paper",
    "3-Resources/courses": "type/assignment",
    "3-Resources/tech": "type/howto",
    "1-Projects/thesis": "project/thesis",
    "1-Projects/mypda": "project/mypda",
    "1-Projects/client-work": "project/thesis",  # general project tag
}


def _scan_topic_tags(
    title: str,
    content: str,
    topics: list[dict[str, str]] | None = None,
) -> list[str]:
    """Scan title+content for topic keywords, return matching tags."""
    combined = (title + " " + content).lower()
    tags: set[str] = set()

    if topics is None:
        # Use legacy constant
        for keyword, tag in TOPIC_PATTERNS:
            if keyword.lower() in combined:
                tags.add(tag)
    else:
        for entry in topics:
            pattern = entry.get("pattern", "")
            tag = entry.get("tag", "")
            if pattern and tag and pattern.lower() in combined:
                tags.add(tag)

    return sorted(tags)


# ---------------------------------------------------------------------------
# Classification rules (config-driven)
# ---------------------------------------------------------------------------

def classify_note(
    filepath: Path,
    config: dict[str, Any] | None = None,
) -> ClassifyResult:
    """Classify a single note based on filename and content patterns.

    Parameters
    ----------
    filepath:
        Path to the markdown file.
    config:
        Full configuration dict (as returned by ``load_config``).
        If *None*, uses built-in defaults.

    Returns a ClassifyResult with destination folder and tags.
    """
    if config is None:
        config = DEFAULT_CONFIG

    org_cfg = config.get("organizer", {})
    rules = org_cfg.get("rules", DEFAULT_CONFIG["organizer"]["rules"])
    topics = org_cfg.get("topics", DEFAULT_CONFIG["organizer"]["topics"])
    folder_tags = org_cfg.get("folder_tags", DEFAULT_CONFIG["organizer"]["folder_tags"])
    delete_empty = org_cfg.get("delete_empty", True)
    empty_min_chars = org_cfg.get("empty_min_chars", 10)
    untitled_min_chars = org_cfg.get("untitled_min_chars", 100)
    inbox_folder = org_cfg.get("inbox_folder", "0-Inbox")

    fm, body = read_frontmatter(filepath)
    title = fm.get("title", filepath.stem) or filepath.stem
    filename = filepath.stem
    # Combine filename + title + first 500 chars of body for matching
    match_text = f"{filename} {title} {body[:500]}"

    # 1. Delete empty/untitled
    if delete_empty and _is_empty_or_untitled(
        filepath, title, body,
        empty_min_chars=empty_min_chars,
        untitled_min_chars=untitled_min_chars,
    ):
        return ClassifyResult(filepath=filepath, dest_folder=DELETE)

    # 2. Apply rules in order
    dest: str | None = None
    for rule in rules:
        match_type = rule.get("match_type", "keywords")

        if match_type == "paper_note":
            if _is_paper_note(title, body):
                dest = rule["destination"]
                break
        else:
            keywords = rule.get("keywords", [])
            case_sensitive = rule.get("case_sensitive", False)
            if keywords and _matches_any(keywords, match_text, case_sensitive=case_sensitive):
                dest = rule["destination"]
                break

    # 3. Fallback -> Inbox
    if dest is None:
        dest = inbox_folder

    # Build tags
    tags: list[str] = []
    folder_tag = folder_tags.get(dest)
    if folder_tag:
        tags.append(folder_tag)
    tags.extend(_scan_topic_tags(title, body, topics=topics))

    return ClassifyResult(filepath=filepath, dest_folder=dest, tags_to_add=tags)


# ---------------------------------------------------------------------------
# Organize vault
# ---------------------------------------------------------------------------

@dataclass
class OrganizeStats:
    moved: int = 0
    deleted: int = 0
    skipped: int = 0
    total: int = 0


def organize_vault(
    vault_dir: Path,
    source_dir: str = "personal",
    dry_run: bool = False,
    config: dict[str, Any] | None = None,
) -> tuple[list[ClassifyResult], OrganizeStats]:
    """Classify and move all .md files in source_dir into PARA folders.

    Parameters
    ----------
    config:
        Full configuration dict.  If *None*, uses built-in defaults.

    Returns (results, stats).
    """
    src = vault_dir / source_dir
    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    md_files = sorted(src.glob("*.md"))
    results: list[ClassifyResult] = []
    stats = OrganizeStats(total=len(md_files))

    for filepath in md_files:
        result = classify_note(filepath, config=config)
        results.append(result)

        if dry_run:
            continue

        if result.dest_folder == DELETE:
            filepath.unlink()
            stats.deleted += 1
            continue

        # Ensure destination directory exists
        dest_dir = vault_dir / result.dest_folder
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Update frontmatter tags before moving
        if result.tags_to_add:
            fm, body = read_frontmatter(filepath)
            existing_tags = fm.get("tags", []) or []
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]
            merged = list(dict.fromkeys(existing_tags + result.tags_to_add))
            fm["tags"] = merged
            write_frontmatter(filepath, fm, body)

        # Move file
        dest_path = dest_dir / filepath.name
        # Handle name collision
        if dest_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_dir / f"{stem} ({counter}){suffix}"
                counter += 1
        shutil.move(str(filepath), str(dest_path))
        stats.moved += 1

    stats.skipped = stats.total - stats.moved - stats.deleted
    return results, stats
