# Verification Matrix

`uv run cpp-playground verify run` executes the declarative suites in [verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml). `uv run cpp-playground verify run --json` emits the same results as structured JSON.

## Core Surface

- `cleanup.one-dockerfile`: the tracked Dockerfile surface is limited to the repo-root `Dockerfile` plus the thin `.devcontainer/Dockerfile.host-user` overlay.
- `bootstrap.install-entrypoint`: `install.sh` stays a thin trampoline into the Python CLI.
- `cli.console-scripts`: `pyproject.toml` exposes the canonical `cpp-playground` console script.

## Image Graph

- `image.stage-names.exact`: the root Dockerfile exposes `base`, `clang`, `gcc`, `final`, and `devcontainer` in order.
- `image.bake-targets`: `docker-bake.hcl` exposes the expected targets and groups.
- `image.bake-print.devcontainer`: resolved Bake output still points at the single root `Dockerfile`.
- `image.final-bootstrap-boundary`: bootstrap inputs are copied before the full repo so non-bootstrap edits do not invalidate the expensive bootstrap layer.

## Devcontainer

- `devcontainer.surface`: `.devcontainer/devcontainer.json` uses the Python CLI for initialize/post-create/post-start hooks, keeps the stable forwarded SSH agent socket path, and the runtime helper owns the default-port, override, and repo-scoped cleanup contract.

## Policy

- `policy.codex-config-surface`: `.codex/` is limited to checked-in project config and role TOML files.
- `policy.no-shell-automation`: repo-owned shell automation is limited to `install.sh`.
- `policy.no-executable-helpers`: repo-owned executable helpers live under `src/cpp_playground/`, not `scripts/`, `.devcontainer/`, or skill-local `scripts/`.
- `hooks.hk-only`: `hk` is the only checked-in hook manager and hook config lives in `hk.pkl`.

## Docs / Skills

- `docs.live-surface`: README, docs, workflows, and repo skills do not point at deprecated `.codex` operational paths or removed helper scripts.
- `docs.canonical-plan`: the canonical merged plan exists and the archived plan/spec/review roots remain present.

## Workflows

- `workflow.hosted-candidate-flow`: the hosted workflow resolves publish decisions through the Python CLI, publishes immutable stage artifacts plus a `sha-*` candidate image, and promotes only after the authoritative self-hosted validation job passes.
- `workflow.pr-source-build-proof`: the self-hosted proof workflow builds from source and uses the Python smoke and verification entrypoints.
