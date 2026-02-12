# Design Philosophy

## Separation of Concerns
- Keep the CLI layer thin and delegating; business logic lives elsewhere.
- Isolate side effects (I/O, storage, network) behind clear boundaries.
- Ensure output formatting is independent from business logic.

## Composition and Extensibility
- Prefer dependency injection over hidden globals.
- Compose features by wiring components at the edges; keep core logic free of wiring.
- Add new features by extending interfaces/factories, not by branching core logic.
- Keep modules cohesive: each module owns its creation and its public API.
- Favor protocol/abstraction-driven design to allow swapping implementations.
- Avoid circular dependencies through clear ownership of creation.

## Configuration-Driven Behavior
- New behavior should be controllable via config, with safe defaults.
- Keep config parsing centralized and explicit to avoid implicit coupling.

## Reliability and Testability
- Ensure resource lifecycle is managed deterministically.
- Add tests and docs with each new feature to keep behavior transparent.

## Writing Rules
- **Absolute imports**: Use `from PaperTracker.module import X`; relative imports are not allowed.
- **Module header and import order**: The first line of every `*.py` file must be a module docstring. After the docstring, place imports in this order: `from __future__ import annotations`, standard library, third-party, and local modules.
- **CLI parameter limits**: The CLI only accepts `--config`; all other parameters must be in YAML config files.
- **Documentation**: All functions under `src` must have Google-style docstrings, and every `*.py` file must start with a module docstring describing its purpose. All the annotation must be in English.
- **Class method ordering**: Put public interface methods near the top of the class; place internal helpers below.
- **Git communication**: Git communication must be in English, including PRs and commits.
- **Function order** place public interfaces (objects called by the main workflow) first, followed by module-internal collaborative functions, and finally underscore-prefixed internal utility functions.
