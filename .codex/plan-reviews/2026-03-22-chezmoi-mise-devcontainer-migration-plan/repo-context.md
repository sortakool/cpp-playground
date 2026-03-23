# Repo Context

- Repo root: `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground`
- Repo path relative to `$HOME`: `dev/github/ray-manaloto/cpp-playground`
- Current public migration plan file: `spec/2026-03-22-chezmoi-mise-devcontainer-migration-plan.md`

## Current Ownership Model

- Repo-generated files owned by the Python control plane:
  - `README.md`
  - `mise.toml`
  - `pixi.toml`
  - `CMakePresets.json`
  - `.devcontainer/devcontainer.json`
  - `.devcontainer/Dockerfile`
  - `docker-bake.hcl`
  - `tooling/cpp26-dev-images/*`
- Current chezmoi source root target: `home/`
- Current chezmoi pin: `2.70.0`

## Current CLI And Task Surfaces

- Current mise tools: `chezmoi, claude-code, codex, gemini-cli, gh, just, node, pixi, python, uv, watchexec`
- Current pixi tasks: `bootstrap, build-cpp26-images, build-devcontainer-image, bump-cpp26-toolchain-pins, check-cpp26-toolchain-pins, devcontainer-up-macos, host-preflight-macos, install-phase0-review-skills, lint-manifests, prove-devcontainer, prove-latest-kernel-ci, prove-latest-kernel-vm, refresh, reuse-lint, review-plan-phase0, review-plan-phase0-dry-run, ruff-check, ruff-format, smoke-ssh-git-gh-parity, smoke-ssh-into-devcontainer, sync-devcontainer-ssh-known-hosts, sync-generated, ty-check, validate-all, validate-repo, validate-runtime`
- Current public mise tasks expected after migration:
  `bootstrap, build-cpp26-images, build-devcontainer-image, bump-cpp26-toolchain-pins, check-cpp26-toolchain-pins, devcontainer-up-macos, host-preflight-macos, install-phase0-review-skills, prove-devcontainer, prove-latest-kernel-ci, prove-latest-kernel-vm, refresh, review-plan-phase0, review-plan-phase0-dry-run, smoke-ssh-git-gh-parity, smoke-ssh-into-devcontainer, sync-devcontainer-ssh-known-hosts, sync-generated, validate-all, validate-repo, validate-runtime`

## Current Devcontainer Wiring

- `remoteUser`: `${localEnv:USER}`
- `postCreateCommand`: `uv run -m tooling post-create`
- `postStartCommand`: `uv run -m tooling ensure-devcontainer-ssh`
- SSH publish arg required by validation: `--publish=127.0.0.1:2222:22`

## Current Validation Invariants

- `mise.toml` must use native aliases such as `claude-code` and `gemini-cli`
- `devcontainer.json` must keep `${localEnv:USER}` as the primary runtime user
- repo-owned shell scripts for build or devcontainer flows are forbidden
- Apple Silicon remains a non-authoritative proof path for Linux `amd64` TSan evidence
