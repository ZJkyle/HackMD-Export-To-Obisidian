"""Tests for notetrans.organizer."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from notetrans.organizer import (
    DELETE,
    ClassifyResult,
    classify_note,
    organize_vault,
    read_frontmatter,
    write_frontmatter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_note(tmp_path: Path, filename: str, title: str, body: str = "Some content here for testing.") -> Path:
    """Create a markdown file with frontmatter in tmp_path."""
    fm = {"title": title, "tags": []}
    dumped = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{dumped}---\n\n{body}"
    path = tmp_path / f"{filename}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Frontmatter tests
# ---------------------------------------------------------------------------

class TestFrontmatter:
    def test_read_frontmatter(self, tmp_path):
        path = _make_note(tmp_path, "test", "My Title", "Hello world")
        fm, body = read_frontmatter(path)
        assert fm["title"] == "My Title"
        assert "Hello world" in body

    def test_read_no_frontmatter(self, tmp_path):
        path = tmp_path / "plain.md"
        path.write_text("Just a plain file", encoding="utf-8")
        fm, body = read_frontmatter(path)
        assert fm == {}
        assert "Just a plain file" in body

    def test_write_frontmatter(self, tmp_path):
        path = tmp_path / "out.md"
        path.write_text("", encoding="utf-8")
        write_frontmatter(path, {"title": "New", "tags": ["a"]}, "Body text")
        fm, body = read_frontmatter(path)
        assert fm["title"] == "New"
        assert fm["tags"] == ["a"]
        assert "Body text" in body


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestClassifyNote:
    def test_empty_note_deleted(self, tmp_path):
        path = _make_note(tmp_path, "empty", "Untitled", "")
        result = classify_note(path)
        assert result.dest_folder == DELETE

    def test_short_untitled_deleted(self, tmp_path):
        path = _make_note(tmp_path, "short", "Untitled", "Hi")
        result = classify_note(path)
        assert result.dest_folder == DELETE

    def test_progress_meeting(self, tmp_path):
        path = _make_note(tmp_path, "0306 Progress Meeting", "0306 Progress Meeting")
        result = classify_note(path)
        assert result.dest_folder == "4-Archive/meetings"
        assert "type/meeting" in result.tags_to_add

    def test_thesis_proposal(self, tmp_path):
        path = _make_note(tmp_path, "Proposal Draft", "Proposal Draft")
        result = classify_note(path)
        assert result.dest_folder == "1-Projects/thesis"
        assert "project/thesis" in result.tags_to_add

    def test_mypda(self, tmp_path):
        path = _make_note(tmp_path, "myPDA design", "myPDA design")
        result = classify_note(path)
        assert result.dest_folder == "1-Projects/mypda"
        assert "project/mypda" in result.tags_to_add

    def test_bankchat(self, tmp_path):
        path = _make_note(tmp_path, "BankChat classifier", "BankChat classifier")
        result = classify_note(path)
        assert result.dest_folder == "1-Projects/client-work"

    def test_course_assignment(self, tmp_path):
        path = _make_note(tmp_path, "VLSI HW3", "VLSI HW3")
        result = classify_note(path)
        assert result.dest_folder == "3-Resources/courses"
        assert "type/assignment" in result.tags_to_add

    def test_tech_llama(self, tmp_path):
        path = _make_note(tmp_path, "llama.cpp build guide", "llama.cpp build guide")
        result = classify_note(path)
        assert result.dest_folder == "3-Resources/tech"
        assert "type/howto" in result.tags_to_add
        assert "topic/llama-cpp" in result.tags_to_add

    def test_career(self, tmp_path):
        path = _make_note(tmp_path, "TSMC Interview", "TSMC Interview")
        result = classify_note(path)
        assert result.dest_folder == "2-Areas/career"

    def test_research_kv_cache(self, tmp_path):
        path = _make_note(tmp_path, "KV Cache eviction", "KV Cache eviction")
        result = classify_note(path)
        assert result.dest_folder == "2-Areas/research"
        assert "topic/kv-cache" in result.tags_to_add

    def test_journal(self, tmp_path):
        path = _make_note(tmp_path, "今日排程", "今日排程")
        result = classify_note(path)
        assert result.dest_folder == "4-Archive/journal"

    def test_personal(self, tmp_path):
        path = _make_note(tmp_path, "Happy New Year", "Happy New Year")
        result = classify_note(path)
        assert result.dest_folder == "4-Archive/personal"

    def test_fallback_inbox(self, tmp_path):
        path = _make_note(tmp_path, "Random thoughts 2024", "Random thoughts 2024")
        result = classify_note(path)
        assert result.dest_folder == "0-Inbox"

    def test_topic_tags_from_content(self, tmp_path):
        path = _make_note(
            tmp_path, "Some Research", "Some Research",
            "We tested MoE and Mixture of Agents together with softmax."
        )
        result = classify_note(path)
        assert "topic/moa" in result.tags_to_add
        assert "topic/moe" in result.tags_to_add
        assert "topic/llm-inference" in result.tags_to_add


# ---------------------------------------------------------------------------
# Organize vault tests
# ---------------------------------------------------------------------------

class TestOrganizeVault:
    def _setup_vault(self, tmp_path):
        """Create a minimal vault with personal/ dir and some notes."""
        personal = tmp_path / "personal"
        personal.mkdir()
        _make_note(personal, "0306 Progress Meeting", "0306 Progress Meeting")
        _make_note(personal, "empty", "Untitled", "")
        _make_note(personal, "llama.cpp setup", "llama.cpp setup")
        _make_note(personal, "Random note", "Random note")
        return tmp_path

    def test_dry_run_does_not_move(self, tmp_path):
        vault = self._setup_vault(tmp_path)
        results, stats = organize_vault(vault, dry_run=True)
        assert stats.total == 4
        assert stats.moved == 0
        assert stats.deleted == 0
        # Files still in personal/
        assert len(list((vault / "personal").glob("*.md"))) == 4

    def test_actual_organize(self, tmp_path):
        vault = self._setup_vault(tmp_path)
        results, stats = organize_vault(vault, dry_run=False)
        assert stats.total == 4
        assert stats.deleted == 1  # empty note
        assert stats.moved == 3
        # Check files moved to correct locations
        assert (vault / "4-Archive/meetings/0306 Progress Meeting.md").exists()
        assert (vault / "3-Resources/tech/llama.cpp setup.md").exists()
        assert (vault / "0-Inbox/Random note.md").exists()
        # personal/ should only have nothing left
        assert len(list((vault / "personal").glob("*.md"))) == 0

    def test_tags_injected(self, tmp_path):
        vault = self._setup_vault(tmp_path)
        organize_vault(vault, dry_run=False)
        # Check that meeting note got type/meeting tag
        meeting_path = vault / "4-Archive/meetings/0306 Progress Meeting.md"
        fm, _ = read_frontmatter(meeting_path)
        assert "type/meeting" in fm.get("tags", [])

    def test_source_dir_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            organize_vault(tmp_path, source_dir="nonexistent")
