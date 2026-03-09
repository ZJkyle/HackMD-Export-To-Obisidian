"""Tests for HackMD API client (mocked)."""

import responses

from notetrans.client import BASE_URL, HackMDClient


@responses.activate
def test_list_notes():
    responses.get(
        f"{BASE_URL}/notes",
        json=[
            {"id": "abc123", "title": "Test Note", "tags": ["python"], "createdAt": 1700000000000},
        ],
    )
    client = HackMDClient("fake-token", delay=0)
    notes = client.list_notes()
    assert len(notes) == 1
    assert notes[0].id == "abc123"
    assert notes[0].title == "Test Note"
    assert notes[0].tags == ["python"]


@responses.activate
def test_get_note():
    responses.get(
        f"{BASE_URL}/notes/abc123",
        json={"id": "abc123", "title": "Test", "content": "# Hello", "tags": []},
    )
    client = HackMDClient("fake-token", delay=0)
    note = client.get_note("abc123")
    assert note.id == "abc123"
    assert note.content == "# Hello"


@responses.activate
def test_list_teams():
    responses.get(
        f"{BASE_URL}/teams",
        json=[{"id": "t1", "path": "myteam", "name": "My Team"}],
    )
    client = HackMDClient("fake-token", delay=0)
    teams = client.list_teams()
    assert len(teams) == 1
    assert teams[0].path == "myteam"


@responses.activate
def test_list_team_notes():
    responses.get(
        f"{BASE_URL}/teams/myteam/notes",
        json=[{"id": "tn1", "title": "Team Note", "tags": []}],
    )
    client = HackMDClient("fake-token", delay=0)
    notes = client.list_team_notes("myteam")
    assert len(notes) == 1
    assert notes[0].team_path == "myteam"


@responses.activate
def test_retry_on_429():
    responses.get(f"{BASE_URL}/notes", status=429)
    responses.get(
        f"{BASE_URL}/notes",
        json=[{"id": "ok", "title": "Recovered", "tags": []}],
    )
    client = HackMDClient("fake-token", delay=0)
    notes = client.list_notes()
    assert len(notes) == 1
    assert notes[0].title == "Recovered"


@responses.activate
def test_bearer_token_sent():
    responses.get(f"{BASE_URL}/me", json={"id": "user1"})
    client = HackMDClient("my-secret-token", delay=0)
    client.get_me()
    assert responses.calls[0].request.headers["Authorization"] == "Bearer my-secret-token"
