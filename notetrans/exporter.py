"""Orchestrate fetching, converting, and writing notes."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml

from notetrans.client import HackMDClient
from notetrans.converter import convert
from notetrans.models import Note

logger = logging.getLogger(__name__)

CHECKPOINT_FILENAME = ".notetrans-checkpoint.json"


def sanitize_filename(title: str) -> str:
    """Derive a safe filename from a note title, preserving CJK/Unicode."""
    name = title.strip()
    if not name:
        name = "Untitled"
    # Remove characters illegal in most file systems
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Truncate to reasonable length
    if len(name) > 200:
        name = name[:200]
    return name


def _unix_ms_to_iso(ts: int) -> str:
    if not ts:
        return ""
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_frontmatter(note: Note) -> str:
    """Generate Obsidian-compatible YAML frontmatter."""
    fm: dict = {"title": note.title}
    if note.tags:
        fm["tags"] = note.tags
    created = _unix_ms_to_iso(note.created_at)
    if created:
        fm["created"] = created
    modified = _unix_ms_to_iso(note.updated_at)
    if modified:
        fm["modified"] = modified
    fm["hackmd_id"] = note.id
    if note.publish_link:
        link = note.publish_link
        if link.startswith("http"):
            fm["source"] = link
        else:
            fm["source"] = f"https://hackmd.io/{link}"
    elif note.permalink:
        fm["source"] = f"https://hackmd.io/{note.permalink}"
    else:
        fm["source"] = f"https://hackmd.io/{note.id}"
    dumped = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{dumped}---\n\n"


def _load_checkpoint(output_dir: Path) -> set[str]:
    """Load exported IDs from an existing checkpoint file."""
    cp_path = output_dir / CHECKPOINT_FILENAME
    if not cp_path.exists():
        return set()
    try:
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        return set(data.get("exported_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_checkpoint(
    output_dir: Path, exported_ids: set[str], started_at: str,
) -> None:
    """Atomically write checkpoint (write .tmp then rename)."""
    cp_path = output_dir / CHECKPOINT_FILENAME
    tmp_path = cp_path.with_suffix(".tmp")
    data = {
        "exported_ids": sorted(exported_ids),
        "started_at": started_at,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(str(tmp_path), str(cp_path))


def _remove_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file on successful completion."""
    cp_path = output_dir / CHECKPOINT_FILENAME
    if cp_path.exists():
        cp_path.unlink()


def export_notes(
    client: HackMDClient,
    output_dir: Path,
    include_teams: bool = False,
    resume: bool = True,
) -> list[dict]:
    """Export all notes. Returns a list of failure dicts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []

    # --- Resume / checkpoint ---
    if resume:
        exported_ids = _load_checkpoint(output_dir)
    else:
        exported_ids = set()

    if exported_ids:
        logger.info("Resuming: %d previously exported notes will be skipped.", len(exported_ids))

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Personal notes ---
    logger.info("Fetching personal note list...")
    personal_notes = client.list_notes()
    logger.info("Found %d personal notes.", len(personal_notes))

    personal_dir = output_dir / "personal"
    personal_dir.mkdir(exist_ok=True)

    _export_note_list(
        client, personal_notes, personal_dir, failures,
        team_path="", exported_ids=exported_ids,
        output_dir=output_dir, started_at=started_at,
    )

    # --- Team notes ---
    if include_teams:
        logger.info("Fetching teams...")
        teams = client.list_teams()
        logger.info("Found %d teams.", len(teams))
        for team in teams:
            logger.info("Fetching notes for team: %s (%s)...", team.name, team.path)
            team_notes = client.list_team_notes(team.path)
            logger.info("  Found %d notes.", len(team_notes))
            team_dir = output_dir / "teams" / team.path
            team_dir.mkdir(parents=True, exist_ok=True)
            _export_note_list(
                client, team_notes, team_dir, failures,
                team_path=team.path, exported_ids=exported_ids,
                output_dir=output_dir, started_at=started_at,
            )

    # Clean finish: remove checkpoint
    _remove_checkpoint(output_dir)

    return failures


def _export_note_list(
    client: HackMDClient,
    notes: list[Note],
    dest_dir: Path,
    failures: list[dict],
    team_path: str,
    exported_ids: set[str],
    output_dir: Path,
    started_at: str,
) -> None:
    used_names: dict[str, int] = {}

    with click.progressbar(notes, label="Exporting", show_pos=True) as bar:
        for note in bar:
            if note.id in exported_ids:
                continue
            try:
                # Fetch full content
                if team_path:
                    full = client.get_team_note(team_path, note.id)
                else:
                    full = client.get_note(note.id)

                # Preserve metadata from list that might be missing in detail
                full.tags = full.tags or note.tags
                full.created_at = full.created_at or note.created_at
                full.updated_at = full.updated_at or note.updated_at
                full.publish_link = full.publish_link or note.publish_link
                full.permalink = full.permalink or note.permalink
                full.team_path = team_path

                body = convert(full.content)
                frontmatter = build_frontmatter(full)
                md_content = frontmatter + body

                # Determine filename, avoiding collisions
                base_name = sanitize_filename(full.title)
                if base_name in used_names:
                    used_names[base_name] += 1
                    file_name = f"{base_name} ({full.id[:8]})"
                else:
                    used_names[base_name] = 1
                    file_name = base_name

                dest = dest_dir / f"{file_name}.md"
                dest.write_text(md_content, encoding="utf-8")

                # Record success in checkpoint
                exported_ids.add(note.id)
                _save_checkpoint(output_dir, exported_ids, started_at)

            except Exception as exc:
                failures.append({
                    "id": note.id,
                    "title": note.title,
                    "error": str(exc),
                })
