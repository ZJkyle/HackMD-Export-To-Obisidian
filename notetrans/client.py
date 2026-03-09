"""HackMD API v1 client."""

from __future__ import annotations

import time

import requests

from notetrans.models import Note, Team

BASE_URL = "https://api.hackmd.io/v1"
MAX_RETRIES = 7
INITIAL_BACKOFF = 2.0


class HackMDClient:
    def __init__(self, token: str, delay: float = 0.5) -> None:
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.delay = delay
        self._last_request_time: float = 0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _request(self, method: str, path: str) -> dict | list:
        self._throttle()
        url = f"{BASE_URL}{path}"
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            self._last_request_time = time.monotonic()
            resp = self.session.request(method, url)

            if resp.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff
                    time.sleep(wait)
                    backoff *= 2
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Max retries exceeded for {url}")  # pragma: no cover

    def get_me(self) -> dict:
        return self._request("GET", "/me")

    def list_notes(self) -> list[Note]:
        data = self._request("GET", "/notes")
        return [Note.from_api(n) for n in data]

    def get_note(self, note_id: str) -> Note:
        data = self._request("GET", f"/notes/{note_id}")
        return Note.from_api(data)

    def list_teams(self) -> list[Team]:
        data = self._request("GET", "/teams")
        return [Team.from_api(t) for t in data]

    def list_team_notes(self, team_path: str) -> list[Note]:
        data = self._request("GET", f"/teams/{team_path}/notes")
        return [Note.from_api(n, team_path=team_path) for n in data]

    def get_team_note(self, team_path: str, note_id: str) -> Note:
        data = self._request("GET", f"/teams/{team_path}/notes/{note_id}")
        return Note.from_api(data, team_path=team_path)
