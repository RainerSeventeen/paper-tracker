# Testing

This repository uses a minimal test layout alongside example configuration
files to validate core query parsing behavior.

## Structure

- `config/test/`: YAML configs dedicated to tests.
- `test/`: Python `unittest` scripts.

## Basic query test

The basic query test ensures that top-level `AND`/`OR`/`NOT` terms in a query
are normalized into the `TEXT` field and that search/output settings are read
correctly.

Files involved:

- `config/test/basic_query.yml`
- `test/test_basic_query.py`

## Running tests

From the repository root:

```bash
python -m unittest discover -s test -p "test_*.py"
```
