# Git Communication Rules

- Git-related communication (PRs, commits, etc.) should be in English.

## PR Summary Format

- **Title line (recommended)**: `<type>(<scope>): <short description> (no-changelog) #<id>`
- **Sections (recommended)**: `Summary`, `Changes`, `Test`, `Notes`
- **Style**:
  - Use concise, factual sentences.
  - Changes listed as bullets with clear file/module names.
  - Testing steps are explicit commands or verification checks.
  - Notes highlight architecture/design implications and extensibility.

### Example Structure

```
<type>(<scope>): <short description> (no-changelog)

## Summary
<1-2 sentences>

### Changes
- <change 1>
- <change 2>

### Test
- <test command / verification>

### Notes
- <design/architecture note>
```
