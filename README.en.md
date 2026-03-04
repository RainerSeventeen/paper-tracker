# Paper Tracker

> The following content was translated using a large language model (LLM)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/rainerseventeen/paper-tracker/releases)
[![Last Commit](https://img.shields.io/github/last-commit/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker/commits)
[![Code Size](https://img.shields.io/github/languages/code-size/rainerseventeen/paper-tracker)](https://github.com/rainerseventeen/paper-tracker)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/rainerseventeen/paper-tracker/graphs/commit-activity)

**English | [中文](./README.md)**

Paper Tracker is a minimal paper tracking tool. Its core goal is to query multiple paper data sources by keywords (`arXiv`, `OpenAlex`) and output structured results based on configuration, so you can continuously track new papers.

**If this project helps you, please consider giving it a Star ⭐. Thank you!**

## Demo

See the live result: [📄 Deployment Page](https://rainerseventeen.github.io/paper-tracker/)

![HTML Output Preview](./docs/assets/html_output_preview.png)

## Implemented Features

- 🔍 **Query and Filtering**:
  - Multi-source retrieval: `arxiv` (preprints), `openalex` (journals/conferences/preprints), can be enabled together
  - Field-based search: `TITLE`, `ABSTRACT`, `AUTHOR`, `JOURNAL`, `CATEGORY`
  - Logical operators: `AND`, `OR`, `NOT`
  - Global `scope` support (applies to all queries)
  - Cross-source deduplication after multi-source aggregation

  | Source | Data Type | Query Field Support | Local Post-Filter | Cross-Source Dedupe |
  |--------|-----------|:-------------------:|:-----------------:|:-------------------:|
  | `arxiv` | Preprints | Full | — | ✅ |
  | `openalex` | Journals / Conferences / Preprints | Partial | ✅ | ✅ |

  > **Note**: The `openalex` source is currently unstable and may return papers unrelated to the queried topic. This feature is still under active development. If you find a significant number of irrelevant articles in the results, it is recommended to disable the `openalex` source in your configuration.

- 🧲 **Fetch Strategy**: Supports fetching older papers to fill the target paper count

- 🗃️ **Deduplication and Storage**: SQLite-based deduplication and paper content storage for later lookup

- 📤 **Output Capabilities**: Supports `json`, `markdown`, `html` output formats, and template replacement

- 🤖 **LLM Enhancement**: Supports OpenAI-compatible API calls, including abstract translation and structured summaries

- 🌐 **Configurable Output Language**: Customize translation and summary output language with `llm.target_lang` (e.g. `Simplified Chinese`, `English`, `Japanese`)

## Quick Start

Using a virtual environment is recommended (e.g. `.venv/`):
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
python -m pip install -e .     # Install
```

Run directly with the built-in example config:
```bash
paper-tracker search --config config/example.yml
```

## Custom Configuration

Copy the example config, edit it as needed, then run:

```bash
cp config/example.yml config/custom.yml
# Edit fields in config/custom.yml
paper-tracker search --config config/custom.yml
```

**Required fields:**

- `queries`: at least one query must be configured
- `llm.base_url` / `llm.model`: required when `llm.enabled: true`

### (Optional) Configure LLM Environment Variables

If LLM summary translation is enabled, configure your API key:

```bash
cp .env.example .env
# Edit .env and fill in your LLM_API_KEY
```

📚 Detailed docs:
- [📖 User Guide](./docs/en/guide_user.md)
- [⚙️ Detailed Configuration Reference](./docs/en/guide_configuration.md)
- [🔍 Search Logic Overview](./docs/en/architecture_search_logic.md)
- [🔍 arXiv Query Syntax](./docs/en/source_arxiv_api_query.md)
- [🔍 OpenAlex Query Parameters](./docs/en/source_openalex_api_query.md)

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
