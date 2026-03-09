"""Convert HackMD-specific syntax to Obsidian-compatible Markdown."""

from __future__ import annotations

import re

# Mapping of HackMD admonition types to Obsidian callout types
CALLOUT_MAP = {
    "info": "info",
    "warning": "warning",
    "success": "success",
    "danger": "danger",
}


def convert(content: str) -> str:
    """Apply all HackMD -> Obsidian transformations."""
    content = _strip_hackmd_frontmatter(content)
    content = _convert_admonitions(content)
    content = _convert_spoilers(content)
    content = _convert_code_blocks(content)
    content = _convert_youtube(content)
    content = _convert_vimeo(content)
    content = _convert_gist(content)
    content = _convert_slideshare(content)
    content = _convert_speakerdeck(content)
    content = _convert_pdf(content)
    content = _convert_underline(content)
    content = _convert_superscript(content)
    content = _convert_subscript(content)
    content = _convert_name_tag(content)
    content = _convert_time_tag(content)
    content = _remove_color_tag(content)
    return content


def _strip_hackmd_frontmatter(content: str) -> str:
    """Remove existing YAML frontmatter (will be replaced by exporter)."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].lstrip("\n")
    return content


def _convert_admonitions(content: str) -> str:
    """Convert :::type ... ::: to Obsidian callouts."""
    pattern = re.compile(
        r"^:::(\w+)\s*\n(.*?)\n^:::\s*$",
        re.MULTILINE | re.DOTALL,
    )

    def _replace(m: re.Match) -> str:
        kind = m.group(1).lower()
        if kind not in CALLOUT_MAP:
            return m.group(0)
        body = m.group(2).rstrip()
        lines = body.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"> [!{CALLOUT_MAP[kind]}]\n{quoted}"

    return pattern.sub(_replace, content)


def _convert_spoilers(content: str) -> str:
    """Convert :::spoiler Title ... ::: to collapsible Obsidian callouts."""
    pattern = re.compile(
        r"^:::spoiler\s*(.*?)\s*\n(.*?)\n^:::\s*$",
        re.MULTILINE | re.DOTALL,
    )

    def _replace(m: re.Match) -> str:
        title = m.group(1) or "Details"
        body = m.group(2).rstrip()
        lines = body.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"> [!info]- {title}\n{quoted}"

    return pattern.sub(_replace, content)


def _convert_code_blocks(content: str) -> str:
    """Remove trailing = from language identifiers in fenced code blocks."""
    return re.sub(r"^```(\w+)=\s*$", r"```\1", content, flags=re.MULTILINE)


def _convert_youtube(content: str) -> str:
    return re.sub(
        r"\{%\s*youtube\s+([\w-]+)\s*%\}",
        r"[YouTube](https://www.youtube.com/watch?v=\1)",
        content,
    )


def _convert_vimeo(content: str) -> str:
    return re.sub(
        r"\{%\s*vimeo\s+([\w-]+)\s*%\}",
        r"[Vimeo](https://vimeo.com/\1)",
        content,
    )


def _convert_gist(content: str) -> str:
    return re.sub(
        r"\{%\s*gist\s+([\w/]+)\s*%\}",
        r"[Gist](https://gist.github.com/\1)",
        content,
    )


def _convert_slideshare(content: str) -> str:
    return re.sub(
        r"\{%\s*slideshare\s+([\w/.-]+)\s*%\}",
        r"[SlideShare](https://www.slideshare.net/\1)",
        content,
    )


def _convert_speakerdeck(content: str) -> str:
    return re.sub(
        r"\{%\s*speakerdeck\s+([\w/.-]+)\s*%\}",
        r"[Speaker Deck](https://speakerdeck.com/\1)",
        content,
    )


def _convert_pdf(content: str) -> str:
    return re.sub(
        r"\{%\s*pdf\s+(https?://\S+)\s*%\}",
        r"[PDF](\1)",
        content,
    )


def _convert_underline(content: str) -> str:
    """Convert ++text++ to <ins>text</ins>."""
    return re.sub(r"\+\+(.+?)\+\+", r"<ins>\1</ins>", content)


def _convert_superscript(content: str) -> str:
    """Convert ^text^ to <sup>text</sup>."""
    return re.sub(r"\^([^\s^][^^]*?)\^", r"<sup>\1</sup>", content)


def _convert_subscript(content: str) -> str:
    """Convert ~text~ to <sub>text</sub>."""
    # Avoid matching ~~strikethrough~~
    return re.sub(r"(?<!~)~([^\s~][^~]*?)~(?!~)", r"<sub>\1</sub>", content)


def _convert_name_tag(content: str) -> str:
    """Convert [name=X] to *-- X*."""
    return re.sub(r"\[name=([^\]]+)\]", r"*-- \1*", content)


def _convert_time_tag(content: str) -> str:
    """Convert [time=T] to *(T)*."""
    return re.sub(r"\[time=([^\]]+)\]", r"*(\1)*", content)


def _remove_color_tag(content: str) -> str:
    """Remove [color=#xxx] tags."""
    return re.sub(r"\[color=#[0-9a-fA-F]{3,6}\]", "", content)
