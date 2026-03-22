# Devcontainer Toolchain Verification Plan

## Purpose

Run the remaining toolchain-completion verification in a fresh session, with the devcontainer as the primary execution surface.

This plan assumes the implementation work is already in the repo and that the next session should focus on verification, failure triage, and minimal corrective patches.

## Hard Constraint

- Do not run validation or prove commands on the host unless there is a specific blocker that cannot be checked from the devcontainer.
- Treat the devcontainer as the default surface for all repo/runtime/toolchain checks.
- Host-side commands are allowed only for:
  - reading files
  - opening the devcontainer
  - lightweight, non-validation setup needed to enter the devcontainer

## Skills To Load

Load skills in this order to minimize re-discovery and keep the workflow aligned with repo policy:

1. Repo router:
   [$python-pixi-astral-toolchain](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/python-pixi-astral-toolchain/SKILL.md)
2. Canonical Python/Astral policy:
   [/Users/rmanaloto/.codex/skills/python-pixi-astral-toolchain/SKILL.md](/Users/rmanaloto/.codex/skills/python-pixi-astral-toolchain/SKILL.md)
3. Repo environment workflow:
   [$pixi-devcontainer](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md)
4. Ruff workflow:
   [$ruff](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/ruff/SKILL.md)
5. Ty workflow:
   [/Users/rmanaloto/.codex/skills/astral-ty/SKILL.md](/Users/rmanaloto/.codex/skills/astral-ty/SKILL.md)
6. uv workflow:
   [/Users/rmanaloto/.codex/skills/uv-package-manager/SKILL.md](/Users/rmanaloto/.codex/skills/uv-package-manager/SKILL.md)
7. Final verification discipline:
   [/Users/rmanaloto/.codex/skills/verification-before-completion/SKILL.md](/Users/rmanaloto/.codex/skills/verification-before-completion/SKILL.md)

Optional only if something fails and targeted debugging is required:

8. Systematic debugging:
   [/Users/rmanaloto/.codex/skills/systematic-debugging/SKILL.md](/Users/rmanaloto/.codex/skills/systematic-debugging/SKILL.md)

## Current Intended State

The repo should now reflect this policy:

- `uv` is the canonical execution path for Python tooling inside the project.
- `pixi` remains the locked environment and task wrapper.
- `ruff` and `ty` are repo-owned uv dev dependencies, not only pixi-provided executables.
- `pixi` tasks wrap `uv run ruff ...` and `uv run ty ...`.
- CI enforces formatting as well as linting and typing.
- repo control-plane `mise` operations isolate themselves from host-global `mise` config.
- generated files touched by the toolchain policy have been re-synced through the control plane.

## Files To Keep In Mind

- [pyproject.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pyproject.toml)
- [uv.lock](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/uv.lock)
- [pixi.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml)
- [tooling/control_plane.py](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/control_plane.py)
- [README.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md)
- [tooling/templates/README.md.tmpl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/README.md.tmpl)
- [tooling/templates/pixi.toml.tmpl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/pixi.toml.tmpl)
- [.github/workflows/tooling-validate.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/tooling-validate.yml)
- [.github/workflows/tooling-refresh.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/tooling-refresh.yml)
- [.github/workflows/latest-kernel-ci.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/latest-kernel-ci.yml)
- [docs/latest-kernel-testing.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/latest-kernel-testing.md)
- [.devcontainer/scripts/post-create.sh](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/scripts/post-create.sh)

## Execution Workflow

### 1. Enter The Devcontainer

- Open the repo in the devcontainer first.
- Do not start with host-side validation commands.

### 2. Bootstrap Inside The Devcontainer

Run:

```bash
python3 -m tooling bootstrap
```

Expected behavior:

- locked pixi environment installs
- repo `mise` tools install through the isolated control-plane path
- `uv sync --locked --group dev` succeeds
- helper uv tools install

If this step fails, stop and fix the smallest root cause before proceeding.

### 3. Run Verification In This Exact Order

Run these in order inside the devcontainer:

```bash
python3 -m tooling validate --mode repo
python3 -m tooling validate --mode runtime
python3 -m tooling validate --mode all
pixi run ruff-check
pixi run ruff-format
pixi run ty-check
uv run ruff check tooling
uv run ruff format --check tooling
uv run ty check tooling
mise install --locked
mise lock
pixi run prove-devcontainer
```

### 4. Failure Handling Policy

- Do not branch into broad cleanup.
- If a command fails:
  - capture the exact failing command
  - identify whether the failure is:
    - devcontainer environment drift
    - repo policy mismatch
    - generated-file drift
    - `mise` isolation bug
    - uv/ruff/ty config issue
    - unrelated pre-existing problem
  - patch only the minimal files required
  - if generated files need updates, re-sync them through the control plane rather than manual patching
  - rerun only the failed command plus the immediately dependent checks

## Specific Things To Verify

### Python Toolchain

- `pixi run ruff-format` passes
- `uv run ruff check tooling` passes
- `uv run ruff format --check tooling` passes
- `uv run ty check tooling` passes
- pixi task wrappers still behave as the checked-in entry points

### Control-Plane Consistency

- `python3 -m tooling bootstrap` uses the same Python toolchain policy described in docs and tasks
- `python3 -m tooling validate --mode repo` confirms generated files are still in sync
- `python3 -m tooling prove --surface devcontainer` still preserves the existing validation behavior

### `mise` Isolation

The key decision was to isolate repo control-plane `mise` operations from host-global config.

Verify that:

- `python3 -m tooling bootstrap` succeeds in the devcontainer without inheriting host-global `mise` config
- `python3 -m tooling refresh` would regenerate repo lockfiles through the isolated path
- plain `mise install --locked` and `mise lock` inside the devcontainer behave acceptably for interactive repo use

If the direct `mise` commands still touch global state in the devcontainer, document the distinction clearly:

- control-plane calls are isolated and policy-compliant
- direct user-invoked `mise` commands remain upstream `mise` behavior

Do not silently weaken the repo control-plane isolation to match upstream default behavior.

## Acceptance Criteria

- all commands in the verification list succeed inside the devcontainer
- no new host-first workflow is introduced
- generated files remain synced via the control plane
- `uv run` and pixi task wrappers agree on Ruff/Ty behavior
- formatting is enforced in CI and passes locally in the devcontainer
- any remaining `mise` caveat is explicit, narrow, and documented

## Output Format For The New Session

At the end of the next session, report:

1. Which verification commands passed unchanged
2. Which commands failed initially
3. What minimal patches were required
4. Whether `pixi run prove-devcontainer` remained green
5. Whether any remaining issue is:
   - fixed
   - intentionally documented
   - blocked on upstream tool behavior

## Notes

- Do not restart broad discovery; this is an execution-focused session.
- Prefer the repo task wrappers and control-plane entry points over ad-hoc command variants.
- Keep the diff tight and policy-driven.
