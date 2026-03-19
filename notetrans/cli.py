"""Click CLI for notetrans."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from notetrans.client import HackMDClient
from notetrans.config import DEFAULT_CONFIG_PATH, generate_default_config, load_config

logger = logging.getLogger(__name__)


def _resolve_token(token: str | None) -> str:
    """Resolve token from --token flag, env var, or .env file."""
    if token:
        return token
    import os

    load_dotenv()
    env_token = os.environ.get("HACKMD_TOKEN", "")
    if env_token:
        return env_token
    logger.error("No token provided. Use --token, HACKMD_TOKEN env var, or .env file.")
    sys.exit(1)


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to YAML config file (default: ~/.config/notetrans/config.yaml).",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress info messages (WARNING and above only).")
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None, verbose: bool, quiet: bool) -> None:
    """notetrans - Export HackMD notes to Obsidian-compatible Markdown."""
    # Configure logging level
    root_logger = logging.getLogger("notetrans")
    if verbose:
        root_logger.setLevel(logging.DEBUG)
    elif quiet:
        root_logger.setLevel(logging.WARNING)

    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)


@cli.command()
@click.option("--token", default=None, help="HackMD API token.")
@click.option("--include-teams", is_flag=True, help="Also export team notes.")
def list(token: str | None, include_teams: bool) -> None:
    """List all accessible notes."""
    token = _resolve_token(token)
    client = HackMDClient(token)

    click.echo("Personal notes:")
    notes = client.list_notes()
    for n in notes:
        tags = f"  [{', '.join(n.tags)}]" if n.tags else ""
        click.echo(f"  {n.id[:8]}  {n.title}{tags}")
    click.echo(f"Total: {len(notes)}")

    if include_teams:
        teams = client.list_teams()
        for team in teams:
            click.echo(f"\nTeam: {team.name} ({team.path})")
            team_notes = client.list_team_notes(team.path)
            for n in team_notes:
                tags = f"  [{', '.join(n.tags)}]" if n.tags else ""
                click.echo(f"  {n.id[:8]}  {n.title}{tags}")
            click.echo(f"Total: {len(team_notes)}")


@cli.command()
@click.option("--token", default=None, help="HackMD API token.")
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=Path("./vault"),
    help="Output directory (default: ./vault).",
)
@click.option("--include-teams", is_flag=True, help="Also export team notes.")
@click.option("--delay", type=float, default=0.5, help="Delay between API requests in seconds.")
def export(token: str | None, output_dir: Path, include_teams: bool, delay: float) -> None:
    """Export notes to Obsidian-compatible Markdown files."""
    token = _resolve_token(token)
    client = HackMDClient(token, delay=delay)

    failures = export_notes(client, output_dir, include_teams=include_teams)

    if failures:
        logger.error("%d note(s) failed to export:", len(failures))
        for f in failures:
            logger.error("  %s  %s: %s", f['id'][:8], f['title'], f['error'])
    else:
        logger.info("All notes exported successfully.")


from notetrans.exporter import export_notes  # noqa: E402


@cli.command()
@click.option(
    "--vault-dir",
    type=click.Path(path_type=Path, exists=True),
    default=Path("./vault"),
    help="Vault directory (default: ./vault).",
)
@click.option(
    "--source-dir",
    default="personal",
    help="Subdirectory to organize (default: personal).",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without moving files.")
@click.pass_context
def organize(ctx: click.Context, vault_dir: Path, source_dir: str, dry_run: bool) -> None:
    """Organize vault notes into PARA folder structure."""
    from notetrans.organizer import DELETE, organize_vault

    config = ctx.obj["config"]

    logger.info("Organizing notes in %s...", vault_dir / source_dir)
    if dry_run:
        click.echo("(dry-run mode - no files will be modified)\n")

    results, stats = organize_vault(vault_dir, source_dir=source_dir, dry_run=dry_run, config=config)

    # Display results grouped by destination
    groups: dict[str, list[str]] = {}
    for r in results:
        dest = r.dest_folder
        groups.setdefault(dest, []).append(r.filepath.name)

    for dest in sorted(groups):
        label = "[DELETE]" if dest == DELETE else dest
        click.echo(f"\n{label} ({len(groups[dest])} notes):")
        for name in groups[dest]:
            click.echo(f"  {name}")

    click.echo(f"\n--- Summary ---")
    click.echo(f"Total: {stats.total}")
    if dry_run:
        delete_count = sum(1 for r in results if r.dest_folder == DELETE)
        move_count = stats.total - delete_count
        click.echo(f"Would move: {move_count}")
        click.echo(f"Would delete: {delete_count}")
    else:
        click.echo(f"Moved: {stats.moved}")
        click.echo(f"Deleted: {stats.deleted}")


@cli.command()
@click.option(
    "--vault-dir",
    type=click.Path(path_type=Path, exists=True),
    default=Path("./vault"),
    help="Vault directory (default: ./vault).",
)
@click.option(
    "--source-dir",
    default="4-Archive/meetings",
    help="Source subdirectory to extract from (default: 4-Archive/meetings).",
)
@click.option(
    "--llm-url",
    default="http://localhost:8000/v1",
    help="vLLM OpenAI-compatible API URL.",
)
@click.option(
    "--llm-api-key",
    default="",
    help="API key for LLM endpoint.",
)
@click.option(
    "--llm-model",
    default="Qwen/Qwen3-VL-8B-Instruct-FP8",
    help="LLM model name.",
)
@click.option("--dry-run", is_flag=True, help="Preview without creating zettel files.")
@click.option("--delay", type=float, default=0.5, help="Delay between LLM calls in seconds.")
@click.pass_context
def extract(
    ctx: click.Context,
    vault_dir: Path,
    source_dir: str,
    llm_url: str,
    llm_api_key: str,
    llm_model: str,
    dry_run: bool,
    delay: float,
) -> None:
    """Extract Zettelkasten permanent notes from meeting/experiment logs via LLM."""
    from notetrans.extractor import extract_zettels

    config = ctx.obj["config"]

    logger.info("Extracting zettels from %s...", vault_dir / source_dir)
    if dry_run:
        click.echo("(dry-run mode - no files will be created)\n")

    zettels, stats = extract_zettels(
        vault_dir,
        source_dir=source_dir,
        llm_url=llm_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        dry_run=dry_run,
        delay=delay,
        config=config,
    )

    for z in zettels:
        tags = f"  [{', '.join(z.tags)}]" if z.tags else ""
        click.echo(f"  [{z.source_title}] -> {z.title}{tags}")

    click.echo(f"\n--- Summary ---")
    click.echo(f"Notes scanned: {stats.notes_scanned}")
    click.echo(f"Zettels {'found' if dry_run else 'created'}: {stats.zettels_created if not dry_run else len(zettels)}")
    click.echo(f"Errors: {stats.errors}")


@cli.command(name="init-config")
def init_config() -> None:
    """Generate a default config file at ~/.config/notetrans/config.yaml."""
    config_dir = DEFAULT_CONFIG_PATH.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    if DEFAULT_CONFIG_PATH.exists():
        click.echo(f"Config file already exists: {DEFAULT_CONFIG_PATH}")
        if not click.confirm("Overwrite?"):
            click.echo("Aborted.")
            return

    content = generate_default_config()
    DEFAULT_CONFIG_PATH.write_text(content, encoding="utf-8")
    click.echo(f"Default config written to {DEFAULT_CONFIG_PATH}")
