"""Tests for HackMD -> Obsidian syntax converter."""

from notetrans.converter import convert


class TestAdmonitions:
    def test_info_callout(self):
        src = ":::info\nSome info text\n:::"
        result = convert(src)
        assert "> [!info]" in result
        assert "> Some info text" in result

    def test_warning_callout(self):
        src = ":::warning\nBe careful\n:::"
        result = convert(src)
        assert "> [!warning]" in result
        assert "> Be careful" in result

    def test_success_callout(self):
        src = ":::success\nAll good\n:::"
        result = convert(src)
        assert "> [!success]" in result

    def test_danger_callout(self):
        src = ":::danger\nDangerous\n:::"
        result = convert(src)
        assert "> [!danger]" in result

    def test_multiline_callout(self):
        src = ":::info\nLine 1\nLine 2\nLine 3\n:::"
        result = convert(src)
        assert "> Line 1" in result
        assert "> Line 2" in result
        assert "> Line 3" in result


class TestSpoiler:
    def test_spoiler_with_title(self):
        src = ":::spoiler Click to reveal\nHidden content\n:::"
        result = convert(src)
        assert "> [!info]- Click to reveal" in result
        assert "> Hidden content" in result

    def test_spoiler_without_title(self):
        src = ":::spoiler\nHidden content\n:::"
        result = convert(src)
        assert "> [!info]- Details" in result


class TestCodeBlocks:
    def test_remove_line_number_marker(self):
        src = "```python=\nprint('hello')\n```"
        result = convert(src)
        assert "```python\n" in result
        assert "```python=" not in result

    def test_plain_code_block_unchanged(self):
        src = "```javascript\nconsole.log('hi')\n```"
        result = convert(src)
        assert "```javascript\n" in result


class TestEmbeds:
    def test_youtube(self):
        src = "{%youtube dQw4w9WgXcQ %}"
        result = convert(src)
        assert "[YouTube](https://www.youtube.com/watch?v=dQw4w9WgXcQ)" in result

    def test_vimeo(self):
        src = "{%vimeo 123456 %}"
        result = convert(src)
        assert "[Vimeo](https://vimeo.com/123456)" in result

    def test_gist(self):
        src = "{%gist user/abc123 %}"
        result = convert(src)
        assert "[Gist](https://gist.github.com/user/abc123)" in result

    def test_pdf(self):
        src = "{%pdf https://example.com/doc.pdf %}"
        result = convert(src)
        assert "[PDF](https://example.com/doc.pdf)" in result


class TestInlineFormatting:
    def test_underline(self):
        assert "<ins>underlined</ins>" in convert("++underlined++")

    def test_superscript(self):
        assert "<sup>sup</sup>" in convert("^sup^")

    def test_subscript(self):
        assert "<sub>sub</sub>" in convert("~sub~")

    def test_strikethrough_not_affected(self):
        result = convert("~~strikethrough~~")
        assert "~~strikethrough~~" in result
        assert "<sub>" not in result


class TestMetaTags:
    def test_name_tag(self):
        assert "*-- Alice*" in convert("[name=Alice]")

    def test_time_tag(self):
        assert "*(2024-01-01)*" in convert("[time=2024-01-01]")

    def test_color_tag_removed(self):
        result = convert("[color=#ff0000]")
        assert "[color=" not in result
        assert result.strip() == ""


class TestFrontmatter:
    def test_strip_existing_frontmatter(self):
        src = "---\ntitle: test\ntags: abc\n---\n\nContent here"
        result = convert(src)
        assert "title: test" not in result
        assert "Content here" in result

    def test_no_frontmatter(self):
        src = "Just content"
        result = convert(src)
        assert "Just content" in result
