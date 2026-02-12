---
name: create-pr
description: "Automate GitHub Pull Request creation using MCP (Model Context Protocol) tools. Use when code changes are committed and you need to create a PR with auto-generated title and description following project commit conventions."
---

# Create PR - Automated Pull Request Creation

Automatically create high-quality Pull Requests using GitHub MCP tools, following conventional commit specifications.

## When to Use

Trigger when user requests PR creation, for example:
- "Create a PR"
- "Help me create a pull request"
- "I finished the refactoring work, can you create a PR?"
- "Create PR for current branch"

**Prerequisites:**
- Code changes are committed to a git branch
- Current branch is not the default branch (main/master)
- Branch is pushed to remote repository (or needs to be pushed before creating PR)

## Workflow

### Step 1: Branch Detection and Validation

Use Bash tool to check current git status:

```bash
# Get current branch
git branch --show-current

# Check for unpushed commits
git status -sb

# Check differences from base branch
git log origin/main..HEAD --oneline
```

**Validation checklist:**
- Current branch is not main/master
- Branch has unmerged commits
- Branch is pushed to remote (if not, push first)

### Step 2: Gather PR Information

Use MCP GitHub tools to fetch commit history:

```bash
# Use MCP tool to get commits for current branch
mcp__github__list_commits owner=<owner> repo=<repo> sha=<current_branch>

# Or use git command to get complete diff and commit info
git log origin/main..HEAD --format="%h %s%n%b"
git diff origin/main...HEAD --stat
```

**Extract information:**
- Extract PR title and description from commit messages
- Identify target base branch (usually main or develop)
- Collect file change statistics
- Find related issue references (e.g., "fix #123")

### Step 3: Generate PR Title and Description

**Title format (strictly follow conventional commit):**

```
<type>(<scope>): <summary>
```

- **Type**: `feat`, `fix`, `perf`, `test`, `docs`, `refactor`, `build`, `ci`, `chore`, `revert`
- **Scope** (optional): e.g., `core`, `API`, `output`, `config`
- **Summary rules**:
  - All content MUST be written in English (including PR title and description)
  - Must start with a lowercase letter
  - Use imperative present tense ("add" not "added")
  - Must not end with a period
  - For breaking changes, add ! before the colon
  - To exclude from changelog, add `(no-changelog)` suffix

**Validation regex:**
```
^(feat|fix|perf|test|docs|refactor|build|ci|chore|revert)(\([a-zA-Z0-9 ]+( Node)?\))?!?: [a-z].+[^.]$
```

**Description template (Paper Tracker format):**
```markdown
## Summary

<1-2 paragraph overview of what this PR does and why>

**Key changes (if applicable):**
- <Key change 1>
- <Key change 2>
- <Key change 3>

### Changes

<Detailed changes, organized by module/component if complex>

- **Module/Component Name** (if multiple modules affected)
  - <Specific change 1>
  - <Specific change 2>
- <Simple change 1>
- <Simple change 2>

## Breaking Changes

<Description of breaking changes, if any. Otherwise omit this section>

## Testing

<Testing approach>
- Tests performed: <description>
OR
- Not run (not requested)
OR
- Not run (docs-only changes)

## Related Issues

<Issue references like "Closes #123" or "N/A">

### Notes

<Optional additional context, caveats, or follow-up items>
```

### Step 4: Create Pull Request

Use MCP GitHub tool to create PR:

```bash
mcp__github__create_pull_request \
  owner=<owner> \
  repo=<repo> \
  title="<conventional_commit_title>" \
  head=<current_branch> \
  base=<base_branch> \
  body="<pr_description>"
```

**Optional parameters:**
- `draft=true` - Create draft PR
- `maintainer_can_modify=true` - Allow maintainer edits

### Step 5: Confirm and Report

After successful creation, report to user:
- PR number and URL
- PR title and target branch
- Number of changed files and statistics

## Title Format Examples

**Good examples:**
- `feat(core): add config override support`
- `fix(output): fix markdown rendering in tables`
- `docs: update environment variables guide`
- `refactor(API)!: change query parameter structure`
- `test(core): add tests for deduplication logic`
- `chore: update dependencies (no-changelog)`

**Bad examples (avoid):**
- `feat: Add feature` - Summary should start with lowercase
- `update code` - Missing type
- `fix(core): fixed bug.` - Past tense and ends with period
- `feature: add support` - Wrong type (should be feat)

## Project-Specific Conventions

For Paper Tracker project:

**Common scopes:**
- `core` - Core logic (query, deduplication, etc.)
- `llm` - LLM integration and services
- `output` - Output formatting and rendering
- `config` - Configuration system
- `API` - API interaction
- `cli` - Command line interface
- `database` - Database schema and storage

**PR Description Guidelines:**
- **Summary section**: Provide 1-2 paragraphs explaining what and why
- **Changes section**: List specific changes, group by module for complex PRs
- **Breaking Changes**: Only include if there are actual breaking changes
- **Testing**: Be explicit about test status:
  - Describe tests run, OR
  - State "Not run (not requested)", OR
  - State "Not run (docs-only changes)"
- **Related Issues**: Use "N/A" if no related issues

**Reference recent commits:**
```bash
# View project commit history to understand style
git log --oneline -n 10
```

## Error Handling

**Common issues and solutions:**

1. **Branch not pushed:**
   ```bash
   git push -u origin <branch_name>
   ```

2. **No unique commits:**
   - Inform user that current branch is same as base branch
   - Suggest making code changes and committing first

3. **MCP tool failure:**
   - Provide clear error messages
   - Suggest checking network connection or GitHub authentication

4. **Title format validation failure:**
   - Display validation errors
   - Provide correct example format
   - Ask user to confirm modified title

## Best Practices

1. **Auto-detect project conventions:**
   - Look for `.github/pull_request_template.md`
   - If template exists, use its structure

2. **Extract issue references:**
   - Find `fix #123`, `closes #456` etc. in commit messages
   - Automatically add to "Related Issue" section of PR description

3. **Branch naming hints:**
   - If type can be inferred from branch name (e.g., `feature/xxx`, `fix/xxx`), prioritize it
   - Cross-validate type consistency with commit messages

4. **Interactive confirmation:**
   - Show preview after generating PR info
   - Ask user if modifications are needed
   - Create PR after confirmation

## Usage Examples

**Scenario 1: Feature PR**
```
User: "Create a PR"
Assistant: Detected current branch feature/markdown-export, creating PR based on 5 commits
          Title: feat(output): add markdown export functionality

          Description preview:
          ## Summary

          Adds markdown export functionality to Paper Tracker, allowing users to export
          paper search results in a customizable markdown format.

          ### Changes
          - Add markdown renderer with template support
          - Add configuration for markdown output
          - Update documentation

          ## Testing
          - Manual testing with sample data

          ## Related Issues
          N/A

          Confirm creation? (use AskUserQuestion tool)
```

**Scenario 2: Refactoring with no changelog**
```
User: "Create PR for config nesting refactor"
Assistant: Title: refactor(core): nest LLM config (no-changelog)

          This will be excluded from changelog due to (no-changelog) marker.
```

**Scenario 3: Breaking change**
```
User: "Create a PR for this API refactoring"
Assistant: Detected breaking changes in configuration schema
          Title: refactor(config)!: change output format structure

          Description will include:
          ## Breaking Changes
          - Configuration field `output.format` renamed to `output.formats`
          - Field now accepts a list instead of single value
```

## Important Notes

- ❌ Don't guess remote repository info, always verify
- ❌ Don't assume branch is pushed before creating PR
- ✅ Ensure all commits are pushed
- ✅ Maintain context awareness of project-specific conventions
- ✅ Provide clear error messages and recovery suggestions
- ✅ Generated PR description should include sufficient context
