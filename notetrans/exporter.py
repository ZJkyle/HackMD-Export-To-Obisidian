"""Orchestrate fetching, converting, and writing notes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml

from notetrans.client import HackMDClient
from notetrans.converter import convert
from notetrans.models import Note


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


def export_notes(
    client: HackMDClient,
    output_dir: Path,
    include_teams: bool = False,
) -> list[dict]:
    """Export all notes. Returns a list of failure dicts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []

    # --- Personal notes ---
    click.echo("Fetching personal note list...")
    personal_notes = client.list_notes()
    click.echo(f"Found {len(personal_notes)} personal notes.")

    personal_dir = output_dir / "personal"
    personal_dir.mkdir(exist_ok=True)

    _export_note_list(client, personal_notes, personal_dir, failures, team_path="")

    # --- Team notes ---
    if include_teams:
        click.echo("Fetching teams...")
        teams = client.list_teams()
        click.echo(f"Found {len(teams)} teams.")
        for team in teams:
            click.echo(f"Fetching notes for team: {team.name} ({team.path})...")
            team_notes = client.list_team_notes(team.path)
            click.echo(f"  Found {len(team_notes)} notes.")
            team_dir = output_dir / "teams" / team.path
            team_dir.mkdir(parents=True, exist_ok=True)
            _export_note_list(
                client, team_notes, team_dir, failures, team_path=team.path,
            )

    return failures


def _export_note_list(
    client: HackMDClient,
    notes: list[Note],
    dest_dir: Path,
    failures: list[dict],
    team_path: str,
) -> None:
    used_names: dict[str, int] = {}

    with click.progressbar(notes, label="Exporting", show_pos=True) as bar:
        for note in bar:
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

            except Exception as exc:
                failures.append({
                    "id": note.id,
                    "title": note.title,
                    "error": str(exc),
                })
