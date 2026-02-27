"""Tests for config override behavior with defaults."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.config import load_config_with_defaults


_BASE_YAML = """
log:
  level: INFO
  to_file: true
  dir: log

queries:
  - NAME: base
    OR:
      - Base Query

search:
  max_results: 5
  pull_every: 7
  fill_enabled: false
  max_lookback_days: 30
  max_fetch_items: 125
  fetch_batch_size: 25

output:
  base_dir: output
  formats: [console]

storage:
  enabled: false
  db_path: database/papers.db
  content_storage_enabled: false
  keep_arxiv_version: false

llm:
  enabled: false
  provider: openai-compat
  base_url: https://api.openai.com
  model: gpt-4o-mini
  api_key_env: LLM_API_KEY
  timeout: 30
  target_lang: zh
  temperature: 0.0
  max_tokens: 800
  max_workers: 3
  max_retries: 3
  retry_base_delay: 1.0
  retry_max_delay: 10.0
  retry_timeout_multiplier: 1.0
  enable_translation: true
  enable_summary: false
"""


class TestConfigOverride(unittest.TestCase):
    def test_override_merges_with_defaults(self) -> None:
        override_yaml = """
log:
  level: DEBUG

search:
  max_results: 10

queries:
  - NAME: override
    OR:
      - Override Query
"""
        with tempfile.TemporaryDirectory() as tmp:
            override_path = Path(tmp) / "override.yml"
            override_path.write_text(override_yaml, encoding="utf-8")

            cfg = load_config_with_defaults(override_path, _defaults_text=_BASE_YAML)

        self.assertEqual(cfg.runtime.level, "DEBUG")
        self.assertEqual(cfg.search.max_results, 10)
        self.assertEqual(cfg.search.sources, ("arxiv",))
        self.assertEqual(cfg.output.formats, ("console",))
        self.assertEqual(len(cfg.search.queries), 1)
        self.assertEqual(cfg.search.queries[0].name, "override")

    def test_empty_override_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            override_path = Path(tmp) / "override.yml"
            override_path.write_text("{}", encoding="utf-8")

            cfg = load_config_with_defaults(override_path, _defaults_text=_BASE_YAML)

        self.assertEqual(cfg.runtime.level, "INFO")
        self.assertEqual(cfg.search.max_results, 5)
        self.assertEqual(cfg.search.sources, ("arxiv",))
        self.assertEqual(len(cfg.search.queries), 1)
        self.assertEqual(cfg.search.queries[0].name, "base")


if __name__ == "__main__":
    unittest.main()
