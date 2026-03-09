"""Data models for HackMD API responses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Note:
    id: str
    title: str
    content: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: int = 0  # unix ms
    updated_at: int = 0  # unix ms
    publish_link: str = ""
    permalink: str = ""
    team_path: str = ""  # non-empty when note belongs to a team

    @classmethod
    def from_api(cls, data: dict, *, team_path: str = "") -> Note:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
            tags=data.get("tags", []) or [],
            created_at=data.get("createdAt", 0),
            updated_at=data.get("lastChangedAt", 0) or data.get("updatedAt", 0),
            publish_link=data.get("publishLink", ""),
            permalink=data.get("permalink", ""),
            team_path=team_path,
        )


@dataclass
class Team:
    id: str
    path: str
    name: str

    @classmethod
    def from_api(cls, data: dict) -> Team:
        return cls(
            id=data.get("id", ""),
            path=data.get("path", ""),
            name=data.get("name", ""),
        )
