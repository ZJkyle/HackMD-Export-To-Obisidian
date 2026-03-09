# notetrans

HackMD to Obsidian Markdown batch exporter.

Fetches all your notes via the HackMD API, converts HackMD-specific syntax to Obsidian-compatible format, and writes `.md` files with proper YAML frontmatter.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

### List notes

```bash
uv run notetrans list --token YOUR_HACKMD_TOKEN
uv run notetrans list --token YOUR_HACKMD_TOKEN --include-teams
```

### Export notes

```bash
uv run notetrans export --token YOUR_HACKMD_TOKEN --output-dir ./vault
uv run notetrans export --token YOUR_HACKMD_TOKEN --output-dir ./vault --include-teams --delay 0.8
```

Options:
- `--token` - HackMD API token (also reads `HACKMD_TOKEN` env var or `.env` file)
- `--output-dir`, `-o` - Output directory (default: `./vault`)
- `--include-teams` - Also export notes from teams you belong to
- `--delay` - Delay between API requests in seconds (default: `0.5`, increase if hitting rate limits)

### Token resolution order

1. `--token` CLI flag
2. `HACKMD_TOKEN` environment variable
3. `.env` file in current directory

## Output structure

```
vault/
├── personal/
│   └── *.md
└── teams/
    └── <team-path>/
        └── *.md
```

Each file includes YAML frontmatter:

```yaml
---
title: Note Title
tags:
- tag1
- tag2
created: '2025-01-01T00:00:00Z'
modified: '2025-01-02T00:00:00Z'
hackmd_id: abc123
source: https://hackmd.io/@user/noteId
---
```

## Syntax conversions

| HackMD | Obsidian |
|---|---|
| `:::info` / `:::warning` / `:::success` / `:::danger` | `> [!info]` / `> [!warning]` / etc. (callouts) |
| `:::spoiler Title` | `> [!info]- Title` (collapsible callout) |
| `` ```lang= `` | `` ```lang `` (remove line number marker) |
| `{%youtube ID %}` | `[YouTube](url)` |
| `{%vimeo/gist/slideshare/speakerdeck/pdf %}` | Corresponding Markdown links |
| `++text++` | `<ins>text</ins>` (underline) |
| `^text^` / `~text~` | `<sup>` / `<sub>` |
| `[name=X]` | `*-- X*` |
| `[time=T]` | `*(T)*` |
| `[color=#xxx]` | Removed |
| Original frontmatter | Stripped and replaced |

## Development

```bash
# Run tests
uv run pytest -v

# Run as module
uv run python -m notetrans --help
```

## Getting your HackMD API token

1. Go to [HackMD Settings](https://hackmd.io/settings)
2. Scroll to **API** section
3. Click **Create API Token**
