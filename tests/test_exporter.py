"""Tests for the exporter module."""

from notetrans.exporter import build_frontmatter, sanitize_filename
from notetrans.models import Note


class TestSanitizeFilename:
    def test_normal_title(self):
        assert sanitize_filename("My Note") == "My Note"

    def test_illegal_characters(self):
        assert sanitize_filename('Note: "test" <1>') == "Note test 1"

    def test_empty_title(self):
        assert sanitize_filename("") == "Untitled"

    def test_whitespace_only(self):
        assert sanitize_filename("   ") == "Untitled"

    def test_cjk_preserved(self):
        result = sanitize_filename("my meeting note")
        assert "meeting" in result

    def test_long_title_truncated(self):
        long_title = "A" * 300
        result = sanitize_filename(long_title)
        assert len(result) == 200


class TestBuildFrontmatter:
    def test_basic_frontmatter(self):
        note = Note(
            id="abc123",
            title="Test Note",
            tags=["python", "test"],
            created_at=1700000000000,
            updated_at=1700001000000,
            publish_link="abc123",
        )
        fm = build_frontmatter(note)
        assert fm.startswith("---\n")
        assert fm.endswith("---\n\n")
        assert "title: Test Note" in fm
        assert "python" in fm
        assert "hackmd_id: abc123" in fm
        assert "source: https://hackmd.io/abc123" in fm

    def test_no_tags(self):
        note = Note(id="x", title="No Tags")
        fm = build_frontmatter(note)
        assert "tags" not in fm

    def test_fallback_source_url(self):
        note = Note(id="xyz789", title="Fallback")
        fm = build_frontmatter(note)
        assert "source: https://hackmd.io/xyz789" in fm

    def test_full_url_publish_link(self):
        note = Note(
            id="abc",
            title="Full URL",
            publish_link="https://hackmd.io/@user/noteId",
        )
        fm = build_frontmatter(note)
        assert "source: https://hackmd.io/@user/noteId" in fm
        assert "hackmd.io/https" not in fm
