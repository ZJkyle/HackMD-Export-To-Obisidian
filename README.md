# notetrans

A CLI tool to export HackMD notes into an Obsidian-compatible vault with automatic PARA classification and LLM-powered knowledge extraction.

## Features

- **HackMD API export** with built-in rate-limit handling and retry logic
- **21 syntax conversion rules** transforming HackMD-specific markup to Obsidian-compatible Markdown
- **PARA auto-classification** with fully customizable keyword rules and topic tagging
- **LLM-powered Zettelkasten extraction** that generates permanent notes from meeting logs and experiment records
- **Resume/checkpoint support** for interrupted exports (skips already-exported notes)
- **Config file support** with deep-merge of user overrides on top of sensible defaults
- **Dry-run mode** for previewing organize and extract operations before committing changes

## Installation

Requires Python 3.11 or later.

### Via pip

```bash
pip install notetrans
```

### Via uv

```bash
uv tool install notetrans
```

### From source

```bash
git clone https://github.com/OWNER/notetrans.git
cd notetrans
uv sync
```

## Quick Start

```bash
# Set your HackMD API token
export HACKMD_TOKEN="your-token-here"

# Export all personal notes to ./vault
notetrans export -o ./vault

# Organize exported notes into PARA folders
notetrans organize --vault-dir ./vault --dry-run

# Extract Zettelkasten permanent notes via LLM
notetrans extract --vault-dir ./vault --dry-run
```

To obtain a HackMD API token, go to [HackMD Settings](https://hackmd.io/settings), scroll to the **API** section, and click **Create API Token**.

## Usage

### Token resolution order

The API token is resolved in the following order:

1. `--token` CLI flag
2. `HACKMD_TOKEN` environment variable
3. `.env` file in the current directory

### Global options

```
--config PATH    Path to YAML config file (default: ~/.config/notetrans/config.yaml)
-v, --verbose    Enable debug logging
-q, --quiet      Suppress info messages (WARNING and above only)
```

### list

List all accessible notes.

```bash
notetrans list
notetrans list --include-teams
```

### export

Export notes to Obsidian-compatible Markdown files with YAML frontmatter.

```bash
notetrans export -o ./vault
notetrans export -o ./vault --include-teams --delay 0.8
```

Options:

- `--token` -- HackMD API token
- `--output-dir`, `-o` -- output directory (default: `./vault`)
- `--include-teams` -- also export notes from teams you belong to
- `--delay` -- delay between API requests in seconds (default: `0.5`; increase if hitting rate limits)

### organize

Classify vault notes into a PARA folder structure based on keyword rules defined in the config file.

```bash
notetrans organize --vault-dir ./vault --dry-run
notetrans organize --vault-dir ./vault --source-dir personal
```

Options:

- `--vault-dir` -- vault root directory (default: `./vault`)
- `--source-dir` -- subdirectory to organize (default: `personal`)
- `--dry-run` -- preview changes without moving files

### extract

Use an OpenAI-compatible LLM endpoint to extract Zettelkasten permanent notes from meeting logs or experiment records.

```bash
notetrans extract --vault-dir ./vault --dry-run
notetrans extract --vault-dir ./vault \
  --llm-url http://localhost:8000/v1 \
  --llm-model Qwen/Qwen3-VL-8B-Instruct-FP8
```

Options:

- `--vault-dir` -- vault root directory (default: `./vault`)
- `--source-dir` -- subdirectory to scan (default: `4-Archive/meetings`)
- `--llm-url` -- OpenAI-compatible API base URL (default: `http://localhost:8000/v1`)
- `--llm-api-key` -- API key for the LLM endpoint
- `--llm-model` -- model name (default: `Qwen/Qwen3-VL-8B-Instruct-FP8`)
- `--delay` -- delay between LLM calls in seconds (default: `0.5`)
- `--dry-run` -- preview without creating zettel files

### init-config

Generate a default configuration file.

```bash
notetrans init-config
```

The config file is written to `~/.config/notetrans/config.yaml`. If the file already exists, you will be prompted before overwriting.

## Configuration

notetrans reads its configuration from `~/.config/notetrans/config.yaml`. User settings are deep-merged on top of built-in defaults, so you only need to specify the values you want to override.

Generate the default config file:

```bash
notetrans init-config
```

### Key config sections

**organizer.rules** -- a list of classification rules. Each rule has a `name`, a `destination` folder, and either a `keywords` list or a special `match_type`. Notes whose title or content match a rule's keywords are moved to the corresponding PARA folder.

**organizer.topics** -- pattern-to-tag mappings. When a note matches a topic pattern, the corresponding tag is added to its frontmatter.

**organizer.folder_tags** -- maps destination folders to tags automatically applied to all notes placed there.

**extractor** -- settings for the LLM extraction endpoint, including `api_base`, `model`, `temperature`, `max_tokens`, `prompt_language` (`"zh"` or `"en"`), and `output_dir`.

See the generated config file for the full list of options with their default values.

## Syntax Conversions

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

## Output Structure

```
vault/
├── personal/
│   └── *.md
└── teams/
    └── <team-path>/
        └── *.md
```

After running `organize`, notes are sorted into PARA folders:

```
vault/
├── 0-Inbox/
├── 1-Projects/
│   ├── thesis/
│   └── client-work/
├── 2-Areas/
│   ├── career/
│   └── research/
├── 3-Resources/
│   ├── papers/
│   ├── courses/
│   └── tech/
└── 4-Archive/
    ├── meetings/
    ├── journal/
    └── personal/
```

Each exported file includes YAML frontmatter:

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

## Development

```bash
# Clone the repository
git clone https://github.com/OWNER/notetrans.git
cd notetrans

# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Run as module
uv run python -m notetrans --help

# Run via CLI entry point
uv run notetrans --help
```

## License

MIT
