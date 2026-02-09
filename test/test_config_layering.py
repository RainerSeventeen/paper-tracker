"""Tests for layered config parsing and validation."""

import sys
import unittest
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.config import parse_config_dict


def _base_raw_config() -> dict:
    return {
        "log": {"level": "INFO", "to_file": True, "dir": "log"},
        "queries": [{"NAME": "q1", "OR": ["test"]}],
        "search": {
            "max_results": 5,
            "pull_every": 7,
            "fill_enabled": False,
            "max_lookback_days": 30,
            "max_fetch_items": 125,
            "fetch_batch_size": 25,
        },
        "output": {
            "base_dir": "output",
            "formats": ["console"],
            "markdown": {
                "template_dir": "template/markdown",
                "document_template": "document.md",
                "paper_template": "paper.md",
                "paper_separator": "\n\n---\n\n",
            },
            "html": {
                "template_dir": "template/html/scholar",
                "document_template": "document.html",
                "paper_template": "paper.html",
            },
        },
        "state": {
            "enabled": True,
            "db_path": "database/papers.db",
            "content_storage_enabled": True,
        },
        "arxiv": {"keep_version": False},
        "llm": {
            "enabled": False,
            "provider": "openai-compat",
            "base_url": "https://api.openai.com",
            "model": "gpt-4o-mini",
            "api_key_env": "LLM_API_KEY",
            "timeout": 30,
            "target_lang": "zh",
            "temperature": 0.0,
            "max_tokens": 800,
            "max_workers": 3,
            "max_retries": 3,
            "retry_base_delay": 1.0,
            "retry_max_delay": 10.0,
            "retry_timeout_multiplier": 1.0,
            "enable_translation": True,
            "enable_summary": False,
        },
    }


class TestConfigLayering(unittest.TestCase):
    def test_parse_success_nested_access(self) -> None:
        cfg = parse_config_dict(_base_raw_config())
        self.assertEqual(cfg.runtime.level, "INFO")
        self.assertEqual(cfg.search.max_results, 5)
        self.assertEqual(cfg.storage.db_path, "database/papers.db")
        self.assertEqual(cfg.search.queries[0].name, "q1")

    def test_output_unknown_format_error_contains_key(self) -> None:
        raw = _base_raw_config()
        raw["output"]["formats"] = ["console", "unknown"]
        with self.assertRaisesRegex(ValueError, "output\\.formats"):
            parse_config_dict(raw)

    def test_search_fill_constraint_error_contains_key(self) -> None:
        raw = _base_raw_config()
        raw["search"]["fill_enabled"] = True
        raw["search"]["pull_every"] = 7
        raw["search"]["max_lookback_days"] = 3
        with self.assertRaisesRegex(ValueError, "search\\.max_lookback_days"):
            parse_config_dict(raw)

    def test_llm_enabled_requires_state_enabled(self) -> None:
        raw = _base_raw_config()
        raw["llm"]["enabled"] = True
        raw["state"]["enabled"] = False
        with self.assertRaisesRegex(ValueError, "state\\.enabled"):
            parse_config_dict(raw)

    def test_llm_enabled_requires_content_storage(self) -> None:
        raw = _base_raw_config()
        raw["llm"]["enabled"] = True
        raw["state"]["content_storage_enabled"] = False
        with self.assertRaisesRegex(ValueError, "state\\.content_storage_enabled"):
            parse_config_dict(raw)

    def test_llm_timeout_type_error_contains_key(self) -> None:
        raw = _base_raw_config()
        raw["llm"]["timeout"] = "30"
        with self.assertRaisesRegex(TypeError, "llm\\.timeout"):
            parse_config_dict(raw)

    def test_queries_empty_error(self) -> None:
        raw = _base_raw_config()
        raw["queries"] = []
        with self.assertRaisesRegex(ValueError, "queries"):
            parse_config_dict(raw)

    def test_markdown_template_non_empty_when_enabled(self) -> None:
        raw = _base_raw_config()
        raw["output"]["formats"] = ["markdown"]
        raw["output"]["markdown"]["template_dir"] = "  "
        with self.assertRaisesRegex(ValueError, "output\\.markdown\\.template_dir"):
            parse_config_dict(raw)

    def test_scope_parsing(self) -> None:
        raw = deepcopy(_base_raw_config())
        raw["scope"] = {"CATEGORY": {"OR": ["cs.CV"]}}
        cfg = parse_config_dict(raw)
        self.assertIsNotNone(cfg.search.scope)
        assert cfg.search.scope is not None
        self.assertIn("CATEGORY", cfg.search.scope.fields)


if __name__ == "__main__":
    unittest.main()
