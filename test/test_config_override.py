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
  sort_by: submittedDate
  sort_order: descending

output:
  format: text
  dir: output

state:
  enabled: false
  db_path: database/papers.db
  content_storage_enabled: false

arxiv:
  keep_version: false

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
            base_path = Path(tmp) / "base.yml"
            override_path = Path(tmp) / "override.yml"
            base_path.write_text(_BASE_YAML, encoding="utf-8")
            override_path.write_text(override_yaml, encoding="utf-8")

            cfg = load_config_with_defaults(override_path, default_path=base_path)

        self.assertEqual(cfg.log_level, "DEBUG")
        self.assertEqual(cfg.max_results, 10)
        self.assertEqual(cfg.output_format, "text")
        self.assertEqual(len(cfg.queries), 1)
        self.assertEqual(cfg.queries[0].name, "override")

    def test_empty_override_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp) / "base.yml"
            override_path = Path(tmp) / "override.yml"
            base_path.write_text(_BASE_YAML, encoding="utf-8")
            override_path.write_text("{}", encoding="utf-8")

            cfg = load_config_with_defaults(override_path, default_path=base_path)

        self.assertEqual(cfg.log_level, "INFO")
        self.assertEqual(cfg.max_results, 5)
        self.assertEqual(len(cfg.queries), 1)
        self.assertEqual(cfg.queries[0].name, "base")


if __name__ == "__main__":
    unittest.main()
