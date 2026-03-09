#!/usr/bin/env bash
# notetrans - Quick launcher script
# Usage:
#   ./run.sh list                          List all HackMD notes
#   ./run.sh export                        Export notes to ./vault
#   ./run.sh organize [--dry-run]          Classify vault into PARA folders
#   ./run.sh extract [--dry-run]           Extract zettel notes via LLM
#   ./run.sh test                          Run tests

set -euo pipefail

# Load .env if present
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
    list)
        uv run notetrans list "$@"
        ;;
    export)
        uv run notetrans export -o ./vault "$@"
        ;;
    organize)
        uv run notetrans organize --vault-dir ./vault "$@"
        ;;
    extract)
        uv run notetrans extract --vault-dir ./vault \
            --llm-url http://localhost:8000/v1 \
            --llm-api-key "${LLM_API_KEY:-}" \
            --llm-model "${LLM_MODEL:-Qwen/Qwen3-VL-8B-Instruct-FP8}" \
            "$@"
        ;;
    test)
        uv run pytest -v "$@"
        ;;
    help|--help|-h)
        echo "notetrans - HackMD to Obsidian exporter + PARA organizer"
        echo ""
        echo "Usage: ./run.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  list                 List all HackMD notes"
        echo "  export               Export notes to ./vault"
        echo "  organize [--dry-run] Classify vault into PARA folders"
        echo "  extract  [--dry-run] Extract zettel notes via LLM"
        echo "  test                 Run tests"
        echo ""
        echo "Environment variables (or .env file):"
        echo "  HACKMD_TOKEN         HackMD API token"
        echo "  LLM_API_KEY          API key for local vLLM"
        echo "  LLM_MODEL            LLM model name (default: Qwen/Qwen3-VL-8B-Instruct-FP8)"
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Run './run.sh help' for usage."
        exit 1
        ;;
esac
