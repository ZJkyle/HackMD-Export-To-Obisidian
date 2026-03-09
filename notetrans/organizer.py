"""Organize vault notes into PARA + Zettelkasten folder structure."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml


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

def _is_empty_or_untitled(filepath: Path, title: str, content: str) -> bool:
    """Note is empty, nearly empty, or has no meaningful title."""
    body = content.strip()
    # Truly empty or only whitespace
    if len(body) < 10:
        return True
    # Title is missing or generic "Untitled"
    if not title or title.strip().lower() == "untitled":
        # But if body has substantial content, keep it
        if len(body) > 100:
            return False
        return True
    return False


def _matches_any(patterns: list[str], text: str) -> bool:
    """Case-insensitive check if any pattern appears in text."""
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


def _scan_topic_tags(title: str, content: str) -> list[str]:
    """Scan title+content for topic keywords, return matching tags."""
    combined = (title + " " + content).lower()
    tags = set()
    for keyword, tag in TOPIC_PATTERNS:
        if keyword.lower() in combined:
            tags.add(tag)
    return sorted(tags)


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

def classify_note(filepath: Path) -> ClassifyResult:
    """Classify a single note based on filename and content patterns.

    Returns a ClassifyResult with destination folder and tags.
    """
    fm, body = read_frontmatter(filepath)
    title = fm.get("title", filepath.stem) or filepath.stem
    filename = filepath.stem
    # Combine filename + title + first 500 chars of body for matching
    match_text = f"{filename} {title} {body[:500]}"

    # 1. Delete empty/untitled
    if _is_empty_or_untitled(filepath, title, body):
        return ClassifyResult(filepath=filepath, dest_folder=DELETE)

    # 2. Projects/thesis
    if _matches_any(["Proposal", "Paper Writing", "Proposed method",
                     "口試", "畢業", "碩二咪", "碩博", "國科會"], match_text):
        dest = "1-Projects/thesis"

    # 3. Projects/mypda
    elif _matches_any(["myPDA", "mypda", "MyPDA"], match_text):
        dest = "1-Projects/mypda"

    # 4. Projects/client-work
    elif _matches_any(["BankChat", "Bankchat", "PoliceChat", "Policechat",
                       "瑛聲", "尊博", "全興"], match_text):
        dest = "1-Projects/client-work"

    # 5. Archive/meetings
    elif _matches_any(["Progress Meeting", "Progress meeting", "進度咪",
                       "Scalable meeting", "BD 例會", "Meet with",
                       "Meet w", "會議紀錄", "會議記錄"], match_text):
        dest = "4-Archive/meetings"

    # 6. Resources/papers
    elif _is_paper_note(title, body):
        dest = "3-Resources/papers"

    # 7. Resources/courses
    elif _matches_any(["Assignment", "Homework", "HW", "Lab ",
                       "ICLAB", "VLSI", "Algorithm", "密碼工程",
                       "生醫電子", "ACAL", "Arch", "DIC",
                       "期中考", "期末", "C++ 學習"], match_text):
        dest = "3-Resources/courses"

    # 8. Resources/tech
    elif _matches_any(["llama.cpp", "Llama.cpp", "Docker", "Raspberry",
                       "Rapsberry", "Setup", "Server", "Cluster",
                       "Cross Compile", "AIAS", "Jetson",
                       "Environment"], match_text):
        dest = "3-Resources/tech"

    # 9. Areas/career
    elif _matches_any(["Interview", "面試", "TSMC"], match_text):
        dest = "2-Areas/career"

    # 10. Areas/research
    elif _matches_any(["KV Cache", "Softmax", "MoA", "MOE", "MoE",
                       "Flash attention", "Splitwise", "StreamLLM",
                       "inference optimization", "Efficient KV",
                       "eviction", "hallucination", "Data distillation",
                       "Data Gen", "Experiment"], match_text):
        dest = "2-Areas/research"

    # 11. Archive/journal
    elif _matches_any(["今日", "每日", "排程", "工作表", "Time Table",
                       "做完的事"], match_text):
        dest = "4-Archive/journal"

    # 12. Archive/personal
    elif _matches_any(["烤肉", "Happy New Year", "first song",
                       "Distance of Blue", "Video making",
                       "image"], match_text):
        dest = "4-Archive/personal"

    # 13. Fallback -> Inbox
    else:
        dest = "0-Inbox"

    # Build tags
    tags: list[str] = []
    folder_tag = FOLDER_TAG_MAP.get(dest)
    if folder_tag:
        tags.append(folder_tag)
    tags.extend(_scan_topic_tags(title, body))

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
) -> tuple[list[ClassifyResult], OrganizeStats]:
    """Classify and move all .md files in source_dir into PARA folders.

    Returns (results, stats).
    """
    src = vault_dir / source_dir
    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    md_files = sorted(src.glob("*.md"))
    results: list[ClassifyResult] = []
    stats = OrganizeStats(total=len(md_files))

    for filepath in md_files:
        result = classify_note(filepath)
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
