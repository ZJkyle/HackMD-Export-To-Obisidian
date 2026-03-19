"""Tests for notetrans.config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from notetrans.config import (
    DEFAULT_CONFIG,
    PROMPTS,
    _deep_merge,
    generate_default_config,
    get_prompt,
    load_config,
)


# ---------------------------------------------------------------------------
# Deep merge tests
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_override_scalar(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result == {"x": {"a": 1, "b": 3, "c": 4}}

    def test_list_replaced_not_merged(self):
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = _deep_merge(base, override)
        assert result["items"] == [4, 5]

    def test_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        _deep_merge(base, override)
        assert base["a"]["b"] == 1


# ---------------------------------------------------------------------------
# Default config structure tests
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    def test_has_organizer_section(self):
        assert "organizer" in DEFAULT_CONFIG

    def test_has_extractor_section(self):
        assert "extractor" in DEFAULT_CONFIG

    def test_organizer_has_rules(self):
        rules = DEFAULT_CONFIG["organizer"]["rules"]
        assert isinstance(rules, list)
        assert len(rules) >= 11  # all classification categories (excluding delete & paper_note = 11 keyword rules)

    def test_organizer_has_topics(self):
        topics = DEFAULT_CONFIG["organizer"]["topics"]
        assert isinstance(topics, list)
        assert len(topics) >= 10

    def test_organizer_has_folder_tags(self):
        folder_tags = DEFAULT_CONFIG["organizer"]["folder_tags"]
        assert isinstance(folder_tags, dict)
        assert "4-Archive/meetings" in folder_tags

    def test_extractor_has_required_keys(self):
        ext = DEFAULT_CONFIG["extractor"]
        assert "api_base" in ext
        assert "model" in ext
        assert "temperature" in ext
        assert "max_tokens" in ext
        assert "prompt_language" in ext
        assert "output_dir" in ext
        assert "delay" in ext

    def test_all_rule_names_unique(self):
        names = [r["name"] for r in DEFAULT_CONFIG["organizer"]["rules"]]
        assert len(names) == len(set(names))

    def test_paper_note_rule_exists(self):
        rules = DEFAULT_CONFIG["organizer"]["rules"]
        paper_rules = [r for r in rules if r.get("match_type") == "paper_note"]
        assert len(paper_rules) == 1


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """When no config file exists and no path given, returns defaults."""
        monkeypatch.setattr("notetrans.config.DEFAULT_CONFIG_PATH", tmp_path / "nonexistent.yaml")
        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_loads_from_explicit_path(self, tmp_path):
        config_file = tmp_path / "custom.yaml"
        user_cfg = {
            "extractor": {
                "model": "my-custom-model",
                "temperature": 0.9,
            },
        }
        config_file.write_text(yaml.dump(user_cfg), encoding="utf-8")

        config = load_config(config_file)
        # Overridden values
        assert config["extractor"]["model"] == "my-custom-model"
        assert config["extractor"]["temperature"] == 0.9
        # Defaults preserved
        assert config["extractor"]["api_base"] == DEFAULT_CONFIG["extractor"]["api_base"]
        assert "organizer" in config

    def test_raises_on_missing_explicit_path(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "does_not_exist.yaml")

    def test_loads_from_default_path_if_exists(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        user_cfg = {"organizer": {"inbox_folder": "99-Inbox"}}
        config_file.write_text(yaml.dump(user_cfg), encoding="utf-8")
        monkeypatch.setattr("notetrans.config.DEFAULT_CONFIG_PATH", config_file)

        config = load_config()
        assert config["organizer"]["inbox_folder"] == "99-Inbox"
        # Other defaults still present
        assert len(config["organizer"]["rules"]) >= 11

    def test_empty_yaml_returns_defaults(self, tmp_path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("", encoding="utf-8")
        config = load_config(config_file)
        assert config == DEFAULT_CONFIG

    def test_partial_organizer_override(self, tmp_path):
        """Overriding organizer.rules replaces the entire list."""
        config_file = tmp_path / "partial.yaml"
        user_cfg = {
            "organizer": {
                "rules": [
                    {"name": "only-rule", "destination": "X", "keywords": ["foo"]},
                ],
            },
        }
        config_file.write_text(yaml.dump(user_cfg), encoding="utf-8")

        config = load_config(config_file)
        assert len(config["organizer"]["rules"]) == 1
        assert config["organizer"]["rules"][0]["name"] == "only-rule"
        # Other organizer keys should still be defaults
        assert config["organizer"]["inbox_folder"] == "0-Inbox"


# ---------------------------------------------------------------------------
# generate_default_config tests
# ---------------------------------------------------------------------------

class TestGenerateDefaultConfig:
    def test_returns_valid_yaml(self):
        text = generate_default_config()
        parsed = yaml.safe_load(text)
        assert isinstance(parsed, dict)
        assert "organizer" in parsed
        assert "extractor" in parsed

    def test_roundtrip(self):
        """Generated YAML can be loaded back and matches DEFAULT_CONFIG."""
        text = generate_default_config()
        parsed = yaml.safe_load(text)
        assert parsed == DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# get_prompt tests
# ---------------------------------------------------------------------------

class TestGetPrompt:
    def test_chinese_prompt(self):
        prompt = get_prompt("zh")
        assert "{title}" in prompt
        assert "{content}" in prompt

    def test_english_prompt(self):
        prompt = get_prompt("en")
        assert "knowledge management assistant" in prompt
        assert "{title}" in prompt
        assert "{content}" in prompt

    def test_unknown_language_falls_back_to_zh(self):
        prompt = get_prompt("fr")
        assert prompt == PROMPTS["zh"]
