# Paper Tracker

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/rainerseventeen/paper-tracker/releases)
[![Last Commit](https://img.shields.io/github/last-commit/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker/commits)
[![Code Size](https://img.shields.io/github/languages/code-size/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/rainerseventeen/paper-tracker/graphs/commit-activity)

**English | [中文](./README.md)**

Paper Tracker is a minimal paper tracking tool. Its core goal is to query arXiv based on keywords (with more sources planned in the future) and output structured results according to configuration, so you can continuously track new papers.

**If this project helps you, please consider giving it a Star ⭐. Thank you!**

## Demo

See the live result: [📄 Deployment Page](https://rainerseventeen.github.io/paper-tracker/)

![HTML Output Preview](./docs/assets/html_output_preview.png)

## Implemented Features

- 🔍 **Query and Filtering**:
  - Query papers via the arXiv API
  - Field-based search: `TITLE`, `ABSTRACT`, `AUTHOR`, `JOURNAL`, `CATEGORY`
  - Logical operators: `AND`, `OR`, `NOT`
  - Global `scope` support (applies to all queries)
- 🧲 **Fetch Strategy**: Supports fetching older papers to fill the target paper count

- 🗃️ **Deduplication and Storage**: SQLite-based deduplication, and stores paper content for later lookup

- 📤 **Output Capabilities**: Supports `json`, `markdown`, `html` output formats, and template replacement

- 🤖 **LLM Enhancement**: Supports OpenAI-compatible API calls, including abstract translation and structured summaries

- 🌐 **Configurable Output Language**: Customize translation and summary output language with `llm.target_lang` (e.g. `Simplified Chinese`, `English`, `Japanese`)

## Quick Start

Using a virtual environment is recommended (e.g. `.venv/`):
```bash
python3 -m venv .venv
```
Install:
```bash
python -m pip install -e .
```

### (Optional) Configure API Environment Variables

If LLM summaries are enabled, configure environment variables:

```bash
cp .env.example .env
# Edit .env and fill in your LLM_API_KEY
```

### Run

```bash
paper-tracker search --config config/default.yml
```

## Custom Configuration

> Note: The project first loads default settings from `config/default.yml`, then loads the file specified by `--config` to override defaults. So please do not modify `default.yml`.

```bash
# Create a custom config file
cp config/default.yml config/custom.yml
```
After editing `config/custom.yml` with your personal settings, run:

```bash
paper-tracker search --config config/custom.yml
```

At minimum, pay attention to these two fields:

- `queries`: configure at least one custom query plan
- `output.formats`: configure at least one output format

📚 Detailed docs:
- [📖 User Guide](./docs/en/guide_user.md)

- [⚙️ Detailed Configuration Reference](./docs/en/guide_configuration.md)

- [🔍 arXiv Query Syntax](./docs/en/source_arxiv_api_query.md)

## Update

To update to the latest version:

```bash
cd paper-tracker
git pull
python -m pip install -e . --upgrade
```

## Feedback

If you encounter issues or have feature suggestions, please open an issue at [GitHub Issues](https://github.com/rainerseventeen/paper-tracker/issues).

Please include runtime logs (default location: `log/`).

## License

This project is licensed under the [MIT License](./LICENSE).

## Acknowledgments

This repository is an independent implementation, inspired by the functional ideas of the following projects:

- [Arxiv-tracker](https://github.com/colorfulandcjy0806/Arxiv-tracker)
- [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)
