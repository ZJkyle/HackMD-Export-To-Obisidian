"""Tests for notetrans.extractor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from notetrans.extractor import (
    ExtractStats,
    ZettelNote,
    _generate_zettel_md,
    _parse_zettel_json,
    _sanitize_filename,
    extract_zettels,
)
from notetrans.organizer import read_frontmatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_note(tmp_path: Path, filename: str, title: str, body: str) -> Path:
    fm = {"title": title, "tags": []}
    dumped = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{dumped}---\n\n{body}"
    path = tmp_path / f"{filename}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# JSON parsing tests
# ---------------------------------------------------------------------------

class TestParseZettelJson:
    def test_valid_json_array(self):
        raw = json.dumps([{"title": "Test", "tags": ["a"], "content": "Hello"}])
        result = _parse_zettel_json(raw)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_empty_array(self):
        assert _parse_zettel_json("[]") == []

    def test_invalid_json(self):
        assert _parse_zettel_json("not json at all") == []

    def test_code_fence_wrapped(self):
        inner = json.dumps([{"title": "X", "tags": [], "content": "Y"}])
        raw = f"```json\n{inner}\n```"
        result = _parse_zettel_json(raw)
        assert len(result) == 1
        assert result[0]["title"] == "X"

    def test_think_block_stripped(self):
        inner = json.dumps([{"title": "A", "tags": [], "content": "B"}])
        raw = f"<think>I need to think about this...</think>\n{inner}"
        result = _parse_zettel_json(raw)
        assert len(result) == 1
        assert result[0]["title"] == "A"

    def test_returns_empty_for_dict(self):
        raw = json.dumps({"title": "Not an array"})
        assert _parse_zettel_json(raw) == []


# ---------------------------------------------------------------------------
# Zettel generation tests
# ---------------------------------------------------------------------------

class TestGenerateZettelMd:
    def test_generates_valid_md(self):
        zettel = ZettelNote(
            title="Test Insight",
            tags=["topic/kv-cache"],
            content="KV cache eviction improves memory usage.",
            source_title="0306 Progress Meeting",
        )
        md = _generate_zettel_md(zettel)
        assert "---" in md
        assert "Test Insight" in md
        assert "[[0306 Progress Meeting]]" in md
        assert "topic/kv-cache" in md


class TestSanitizeFilename:
    def test_removes_illegal_chars(self):
        assert _sanitize_filename('a<b>c:d"e') == "abcde"

    def test_empty_becomes_untitled(self):
        assert _sanitize_filename("") == "Untitled Zettel"

    def test_truncates_long_names(self):
        long_name = "x" * 300
        assert len(_sanitize_filename(long_name)) == 200


# ---------------------------------------------------------------------------
# extract_zettels integration test
# ---------------------------------------------------------------------------

class TestExtractZettels:
    def test_source_dir_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_zettels(tmp_path, source_dir="nonexistent")

    def test_dry_run_no_files_created(self, tmp_path):
        source = tmp_path / "4-Archive" / "meetings"
        source.mkdir(parents=True)
        _make_note(source, "meeting1", "Meeting 1", "Discussion about KV cache " * 20)

        llm_response = json.dumps([
            {"title": "KV Cache Insight", "tags": ["topic/kv-cache"], "content": "Important insight."}
        ])

        with patch("notetrans.extractor._call_llm", return_value=llm_response):
            zettels, stats = extract_zettels(
                tmp_path,
                source_dir="4-Archive/meetings",
                dry_run=True,
                delay=0,
            )

        assert len(zettels) == 1
        assert zettels[0].title == "KV Cache Insight"
        # No files should be created in dry-run
        research_dir = tmp_path / "2-Areas" / "research"
        if research_dir.exists():
            assert len(list(research_dir.glob("*.md"))) == 0

    def test_actual_extraction(self, tmp_path):
        source = tmp_path / "4-Archive" / "meetings"
        source.mkdir(parents=True)
        _make_note(source, "meeting1", "Meeting 1", "Discussion about MoA approach " * 20)

        llm_response = json.dumps([
            {"title": "MoA Architecture", "tags": ["topic/moa"], "content": "MoA uses multiple agents."}
        ])

        with patch("notetrans.extractor._call_llm", return_value=llm_response):
            zettels, stats = extract_zettels(
                tmp_path,
                source_dir="4-Archive/meetings",
                dry_run=False,
                delay=0,
            )

        assert stats.zettels_created == 1
        dest = tmp_path / "2-Areas" / "research" / "MoA Architecture.md"
        assert dest.exists()
        fm, body = read_frontmatter(dest)
        assert "[[Meeting 1]]" in fm.get("source", "")

    def test_skips_short_notes(self, tmp_path):
        source = tmp_path / "4-Archive" / "meetings"
        source.mkdir(parents=True)
        _make_note(source, "short", "Short Note", "Hi")

        with patch("notetrans.extractor._call_llm") as mock_llm:
            zettels, stats = extract_zettels(
                tmp_path,
                source_dir="4-Archive/meetings",
                dry_run=True,
                delay=0,
            )

        mock_llm.assert_not_called()
        assert len(zettels) == 0

    def test_handles_llm_error(self, tmp_path):
        source = tmp_path / "4-Archive" / "meetings"
        source.mkdir(parents=True)
        _make_note(source, "meeting1", "Meeting 1", "Content " * 20)

        with patch("notetrans.extractor._call_llm", side_effect=Exception("Connection error")):
            zettels, stats = extract_zettels(
                tmp_path,
                source_dir="4-Archive/meetings",
                dry_run=False,
                delay=0,
            )

        assert stats.errors == 1
        assert len(zettels) == 0
