# Ruff Integration Reference

Use this reference when the task includes editor setup, pre-commit hooks, CI, containers, or migration from older Python tooling.

## Editor Setup

### VS Code

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.importStrategy": "fromEnvironment"
}
```

Install the extension:

```bash
code --install-extension charliermarsh.ruff
```

## Pre-commit

Put Ruff's lint hook before Ruff's formatter hook when using `--fix`.

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.7
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

Exclude notebooks by restricting file types:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.7
    hooks:
      - id: ruff-check
        types_or: [python, pyi]
        args: [--fix]
      - id: ruff-format
        types_or: [python, pyi]
```

## GitHub Actions

Minimal workflow with the official action:

```yaml
name: Ruff

on: [push, pull_request]

jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
```

Run custom arguments:

```yaml
- uses: astral-sh/ruff-action@v3
  with:
    args: check --output-format github
```

Split lint and format checks:

```yaml
jobs:
  ruff-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
        with:
          args: check --output-format github

  ruff-format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
        with:
          args: format --check --diff
```

## Docker

Use the published container when the repo or CI prefers containerized tools:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/astral-sh/ruff:0.15.7-alpine check .
docker run --rm -v "$PWD:/work" -w /work ghcr.io/astral-sh/ruff:0.15.7-alpine format --check .
```

## Migration Notes

Map common older tools to Ruff:

```text
black .                -> ruff format .
black --check .        -> ruff format --check .
flake8 .               -> ruff check .
isort .                -> ruff check --select I --fix .
```

Keep migration scoped. Do not rewrite unrelated files just to standardize on Ruff unless the user explicitly wants that migration.
