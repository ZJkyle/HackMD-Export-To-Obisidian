"""Tests for the exporter module."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from notetrans.exporter import (
    CHECKPOINT_FILENAME,
    _load_checkpoint,
    _remove_checkpoint,
    _save_checkpoint,
    build_frontmatter,
    export_notes,
    sanitize_filename,
)
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


def _make_mock_client(notes: list[Note]) -> MagicMock:
    """Create a mock HackMDClient that returns the given notes."""
    client = MagicMock()
    client.list_notes.return_value = notes
    client.get_note.side_effect = lambda nid: next(
        n for n in notes if n.id == nid
    )
    return client


class TestCheckpointHelpers:
    def test_load_checkpoint_no_file(self, tmp_path):
        assert _load_checkpoint(tmp_path) == set()

    def test_save_and_load_checkpoint(self, tmp_path):
        ids = {"id1", "id2"}
        _save_checkpoint(tmp_path, ids, "2025-01-01T00:00:00Z")
        loaded = _load_checkpoint(tmp_path)
        assert loaded == ids

        # Verify JSON structure
        data = json.loads((tmp_path / CHECKPOINT_FILENAME).read_text())
        assert sorted(data["exported_ids"]) == ["id1", "id2"]
        assert data["started_at"] == "2025-01-01T00:00:00Z"
        assert "last_updated" in data

    def test_remove_checkpoint(self, tmp_path):
        _save_checkpoint(tmp_path, {"id1"}, "2025-01-01T00:00:00Z")
        assert (tmp_path / CHECKPOINT_FILENAME).exists()
        _remove_checkpoint(tmp_path)
        assert not (tmp_path / CHECKPOINT_FILENAME).exists()

    def test_remove_checkpoint_no_file(self, tmp_path):
        # Should not raise
        _remove_checkpoint(tmp_path)

    def test_load_corrupt_checkpoint(self, tmp_path):
        (tmp_path / CHECKPOINT_FILENAME).write_text("not json")
        assert _load_checkpoint(tmp_path) == set()


class TestCheckpointExport:
    def _make_notes(self):
        return [
            Note(id="note1", title="Note 1", content="# Note 1"),
            Note(id="note2", title="Note 2", content="# Note 2"),
            Note(id="note3", title="Note 3", content="# Note 3"),
        ]

    def test_checkpoint_created_during_export(self, tmp_path):
        """Checkpoint file is created during export and removed on completion."""
        notes = self._make_notes()
        client = _make_mock_client(notes)

        # Track checkpoint existence during export
        checkpoint_existed = []
        original_get = client.get_note.side_effect

        def tracking_get(nid):
            result = original_get(nid)
            # After first note is written, checkpoint should exist
            # (checked after second call)
            cp = tmp_path / CHECKPOINT_FILENAME
            checkpoint_existed.append(cp.exists())
            return result

        client.get_note.side_effect = tracking_get

        failures = export_notes(client, tmp_path, resume=True)
        assert failures == []
        # Checkpoint should be cleaned up after successful completion
        assert not (tmp_path / CHECKPOINT_FILENAME).exists()
        # Checkpoint should have existed during export (after first note)
        assert any(checkpoint_existed)

    def test_resume_skips_already_exported(self, tmp_path):
        """Resume mode skips notes that are already in the checkpoint."""
        notes = self._make_notes()
        client = _make_mock_client(notes)

        # Pre-populate checkpoint with note1 and note2
        _save_checkpoint(tmp_path, {"note1", "note2"}, "2025-01-01T00:00:00Z")
        (tmp_path / "personal").mkdir(parents=True, exist_ok=True)

        failures = export_notes(client, tmp_path, resume=True)
        assert failures == []

        # Only note3 should have been fetched
        client.get_note.assert_called_once_with("note3")

        # Checkpoint cleaned up on success
        assert not (tmp_path / CHECKPOINT_FILENAME).exists()

    def test_fresh_export_ignores_checkpoint(self, tmp_path):
        """When resume=False, existing checkpoint is ignored."""
        notes = self._make_notes()
        client = _make_mock_client(notes)

        # Pre-populate checkpoint
        _save_checkpoint(tmp_path, {"note1", "note2"}, "2025-01-01T00:00:00Z")

        failures = export_notes(client, tmp_path, resume=False)
        assert failures == []

        # All three notes should have been fetched
        assert client.get_note.call_count == 3

        # Checkpoint cleaned up
        assert not (tmp_path / CHECKPOINT_FILENAME).exists()

    def test_checkpoint_cleanup_on_success(self, tmp_path):
        """Checkpoint file is removed after all notes export successfully."""
        notes = [Note(id="only1", title="Only", content="content")]
        client = _make_mock_client(notes)

        failures = export_notes(client, tmp_path, resume=True)
        assert failures == []
        assert not (tmp_path / CHECKPOINT_FILENAME).exists()

        # The note file should exist
        assert (tmp_path / "personal" / "Only.md").exists()
