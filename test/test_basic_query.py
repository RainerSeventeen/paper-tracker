"""Tests for basic query configuration parsing."""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PaperTracker.config import load_config


class TestBasicQueryConfig(unittest.TestCase):
    def test_basic_query_config_parsing(self) -> None:
        config_path = REPO_ROOT / "config" / "test" / "basic_query.yml"

        cfg = load_config(config_path)

        self.assertEqual(cfg.log_level, "INFO")
        self.assertEqual(cfg.max_results, 5)
        self.assertEqual(cfg.sort_by, "submittedDate")
        self.assertEqual(cfg.sort_order, "descending")
        self.assertEqual(cfg.output_format, "json")

        self.assertEqual(len(cfg.queries), 1)
        query = cfg.queries[0]
        self.assertEqual(query.name, "basic")
        self.assertIn("TEXT", query.fields)
        text_field = query.fields["TEXT"]
        self.assertEqual(text_field.OR, ("machine learning", "deep learning"))
        self.assertEqual(text_field.AND, ("neural network",))
        self.assertEqual(text_field.NOT, ("survey",))


if __name__ == "__main__":
    unittest.main()
