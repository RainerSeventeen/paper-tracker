# Repository Guidelines

## Project Structure & Module Organization

- `src/PaperTracker/` contains the Python package. Key areas: `core/` (models/query logic), `sources/arxiv/` (API client and parsing), `services/` (search orchestration), `renderers/` (CLI output), `utils/` (logging/helpers), `cli.py` (entrypoint).
- `config/default.yml` is the sample configuration used by the CLI.
- `docs/` contains project docs (configuration and arXiv API query notes).
- `build/` contains build artifacts; avoid editing manually.

## Build, Test, and Development Commands

- Install in editable mode:
  - `python -m pip install -e .`
- Run a search with the sample config:
  - `paper-tracker --config config/default.yml search`
- There is no documented test command in this repository; if you add tests, document the command in this file and the README.

## Coding Style & Naming Conventions

- Follow standard Python style (PEP 8): 4-space indentation, `snake_case` for functions/variables, `CapWords` for classes, `lowercase` module names.
- Keep CLI flags and configuration keys consistent with existing conventions in `config/default.yml` and `src/PaperTracker/config.py`.
- Add annotation (Google style docstring) for every function in English. Same as the new files, at the top of the `*,py`

## Testing Guidelines

- No automated tests are present in the repo today.
- If you add tests, create a `tests/` directory, name files `test_*.py`, and document how to run them (e.g., `pytest`) in this guide.

## Commit & Pull Request Guidelines

- Commit messages follow a lightweight Conventional Commits style seen in history (e.g., `feat: add query expression`).
- Keep commits focused and include a short, present-tense subject.
- For PRs, include: a brief description, how to run or verify changes, and any config or behavior changes. Add screenshots only if CLI output format changes.

## Configuration Tips

- Use `config/default.yml` as the starting point for new environments.
- If you change config schema or defaults, update `docs/configuration.md` alongside the code.
