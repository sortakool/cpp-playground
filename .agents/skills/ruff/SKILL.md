---
name: ruff
description: Use Ruff for Python linting, formatting, import sorting, and Ruff-related project setup. Trigger when working in Python projects that already use Ruff (`[tool.ruff]`, `ruff.toml`, `.ruff.toml`, `ruff check`, `ruff format`, `ruff-pre-commit`), when replacing Black/Flake8/isort workflows, or when adding Ruff to editors, pre-commit, or CI.
---

# Ruff

Use this skill to lint, auto-fix, format, and integrate Ruff in Python projects without creating noisy repo-wide churn.

## Workflow

1. Detect whether the project already uses Ruff.
2. Choose the correct Ruff invocation for the project environment.
3. Limit scope to the files being changed unless the user asks for a broader sweep.
4. Run lint fixes before formatting.
5. Verify with check-only commands after making changes.
6. Read [references/integration.md](references/integration.md) only when editor, pre-commit, CI, or migration setup is part of the task.

## Detect Ruff Usage

Prefer Ruff when you see any of the following:

- `[tool.ruff]` in `pyproject.toml`
- `ruff.toml` or `.ruff.toml`
- `ruff check` or `ruff format` in scripts, CI, or docs
- `astral-sh/ruff-pre-commit` or `astral-sh/ruff-action`

If the project does not already use Ruff and the user did not ask to introduce it, avoid adding Ruff-specific churn.

## Choose Invocation

Use the project-pinned Ruff when possible:

- `uv run ruff ...`: Ruff is part of the project's dependencies or the repo uses `uv`.
- `ruff ...`: Ruff is already available in the active environment or toolchain.
- `uvx ruff ...`: Ruff is not installed in the project and you need a one-off run.

## Scope Rules

- Default to touched files and relevant directories, not the whole repository.
- Use `ruff format --diff <paths>` before formatting files with large pre-existing style drift.
- Skip repo-wide formatting if the diff shows broad unrelated rewrites and the user did not ask for a full format pass.
- Treat `--unsafe-fixes` as opt-in. Preview first, then apply only with clear justification.

## Core Commands

```bash
# Lint
ruff check path/to/file.py
ruff check src tests
ruff check --select I path/to/file.py
ruff rule F401

# Apply safe fixes
ruff check --fix path/to/file.py

# Preview or apply unsafe fixes carefully
ruff check --unsafe-fixes --diff path/to/file.py
ruff check --fix --unsafe-fixes path/to/file.py

# Format
ruff format --diff path/to/file.py
ruff format path/to/file.py
ruff format --check path/to/file.py

# Typical touched-file workflow
ruff check --fix path/to/file.py
ruff format path/to/file.py
ruff check path/to/file.py
ruff format --check path/to/file.py
```

## Common Patterns

### Lint Only

Use `ruff check <paths>` when the task is to inspect violations, enforce rules in CI, or explain a rule failure.

### Import Sorting

Use `ruff check --select I --fix <paths>` when the task is specifically import ordering or isort replacement.

### Formatting

Use `ruff format --diff <paths>` before applying formatting when you need to gauge churn. Apply `ruff format <paths>` only after confirming scope is acceptable.

### Full Touched-File Cleanup

Use this order:

```bash
ruff check --fix <paths>
ruff format <paths>
ruff check <paths>
ruff format --check <paths>
```

Lint fixes can rewrite imports or code structure; formatting should run after them.

## Configuration Guidance

- Ruff uses the closest configuration file for a given file.
- Ruff does not merge parent configs automatically.
- Use `extend = "../pyproject.toml"` or another explicit path when inheriting shared settings.
- Prefer project configuration over command-line rule sprawl for persistent behavior.

## Guardrails

- Do not run `ruff check --fix .` or `ruff format .` by default in a large repo.
- Do not replace Black, Flake8, or isort configuration unless the user asks for migration work.
- Do not use Ruff as a substitute for type checking or test execution.
- Explain non-obvious rule codes with `ruff rule <CODE>` before changing behavior-sensitive code.

## Integration Tasks

For editor setup, pre-commit hooks, GitHub Actions, Docker usage, and migration notes, read [references/integration.md](references/integration.md).
