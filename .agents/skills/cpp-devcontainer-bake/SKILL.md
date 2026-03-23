---
name: cpp-devcontainer-bake
description: Orchestrate this repository's host-aware devcontainer lifecycle around `docker-bake.hcl`, `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, `tooling/control_plane.py`, `mise.toml`, and `pixi.toml`. Use when building or rebuilding `cpp-devcontainer`, debugging username parity, SSH-agent or `gh` auth in the devcontainer, reviewing the `dev_base` or `cpp26_*` Bake graph, or coordinating the repo's chezmoi host bootstrap with the container's post-create and post-start flows.
---

# C++ Devcontainer Bake

## Overview

Use this skill for the repo-specific devcontainer lifecycle. This is not a generic devcontainer generator and not a generic one-shot `docker buildx bake dev` workflow.

## Load Order

1. Load `$python-pixi-astral-toolchain` for repo-owned Python, Pixi, uv, and mise policy.
2. Load `$pixi-devcontainer` for the checked-in bootstrap, validate, and prove flows.
3. Load `$cpp26-dev-image-build` when the task touches base compiler images, toolchain pins, or `cpp26_*` targets.
4. Load `$cpp26-dev-image-validate` only when the user specifically asks to validate the compiler images before publish or project use.

## Source Of Truth

- `docker-bake.hcl`
- `.devcontainer/Dockerfile`
- `.devcontainer/devcontainer.json`
- `docs/mac-devcontainer-parity.md`
- `tooling/control_plane.py`
- `tooling/tool-version-manifest.json`
- `mise.toml`
- `pixi.toml`

Read [references/repo-build-surface.md](references/repo-build-surface.md) before changing commands or explaining how the targets compose.
Read [references/docker-bake-guidance.md](references/docker-bake-guidance.md) when editing Bake semantics or explaining why the build graph exists.
Read [references/host-parity-and-bootstrap.md](references/host-parity-and-bootstrap.md) when the task touches host bootstrap, secrets, SSH, `gh`, or editor-vs-CLI devcontainer startup.

## Workflow

1. Use the Python control plane as the default local build path:

```bash
python3 -m tooling build-devcontainer-image --image-tag dev
```

Treat that as authoritative for local development. It is a host-aware staged build, not a thin alias for `docker buildx bake dev`.

2. Inspect the current Bake graph only when you need to explain or debug it:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print dev_base
docker buildx bake -f docker-bake.hcl --print dev
```

3. Understand the current local build sequence before proposing changes. `tooling/control_plane.py` currently:

- resolves `DEVCONTAINER_USERNAME` from the host short username
- materializes `dev_base`, `cpp26_clang_core`, and `cpp26_gcc_core` locally with `output=type=docker`
- clears registry cache import and export for those local materialization steps
- runs a final `docker buildx build --load -f .devcontainer/Dockerfile`
- points that final build at the locally materialized images with explicit `BASE_IMAGE`, `CLANG_IMAGE`, and `GCC_IMAGE` build args
- injects `DEVCONTAINER_USERNAME` from the host short username

Do not collapse that back into a generic direct-Bake recipe unless the user is explicitly changing the build system.

4. If the task is about base compiler images instead of the wrapper image, delegate to `$cpp26-dev-image-build` or run:

```bash
python3 -m tooling build-cpp26-images --toolchain all --flavor core --image-tag dev
```

5. After a successful host build, report the host-aware handoff:

```bash
python3 -m tooling print-devcontainer-env cpp-devcontainer:dev
```

6. For the macOS CLI path, run the host-side preflight and startup sequence:

```bash
python3 -m tooling host-preflight-macos
python3 -m tooling devcontainer-up-macos
python3 -m tooling sync-devcontainer-ssh-known-hosts
python3 -m tooling smoke-ssh-into-devcontainer
```

7. For editor-managed startup, build the image first, then let the editor own the actual container attach flow. After the container is up, use the same in-container bootstrap and smoke checks.

8. Inside the container, the checked-in lifecycle is:

```bash
python3 -m tooling post-create
gh auth login --git-protocol ssh
gh auth status
python3 -m tooling smoke-ssh-git-gh-parity
```

`postCreateCommand` already runs `python3 -m tooling post-create`, and `postStartCommand` already runs `python3 -m tooling ensure-devcontainer-ssh`. Prefer explaining those hooks over inventing ad-hoc shell scripts.

9. Runtime proof belongs to the locked devcontainer workflow, not the image build itself:

```bash
python3 -m tooling validate --mode all
pixi run prove-devcontainer
```

## Decision Rules

- Routine build or rebuild for local use: `python3 -m tooling build-devcontainer-image`
- Need to see resolved graph state before changing anything: `docker buildx bake --print dev_base` and `docker buildx bake --print dev`
- Need to list the root groups and targets: `docker buildx bake --list=targets`
- Need different compiler-image tags or registry prefixes: `$cpp26-dev-image-build`
- Need macOS CLI startup with host SSH-agent forwarding: `python3 -m tooling devcontainer-up-macos`
- Need host-local SSH verification into the container: `python3 -m tooling sync-devcontainer-ssh-known-hosts` and `python3 -m tooling smoke-ssh-into-devcontainer`
- Need post-build bootstrap, validate, or prove flows: `$pixi-devcontainer`
- Need Python-tooling or control-plane policy questions: `$python-pixi-astral-toolchain`

## Guardrails

- Keep the root `docker-bake.hcl` as the build graph and `tooling/control_plane.py` as the orchestration layer.
- Do not replace the local control-plane build path with a generic `docker buildx bake dev` recipe.
- Do not generate `docker-compose.yml`, `setup.sh`, or README patterns from generic devcontainer templates for this repo.
- Do not recommend `remoteUser: root`; this repo requires `remoteUser=${localEnv:USER}` with `updateRemoteUserUID=true`.
- Do not bind-mount host `~/.claude`, `~/.codex`, `~/.gemini`, or host `~/.ssh`; this repo intentionally uses named volumes plus SSH-agent socket forwarding.
- Do not move host bootstrap into the container. `chezmoi` owns host shell/bootstrap, `mise.toml` owns repo CLI pins and redaction rules, `pixi.toml` owns locked tasks and environments, and `.devcontainer/Dockerfile` owns baked-in tools.
- Do not store long-lived tokens in `devcontainer.json`.
- Do not relax the repo's `linux/amd64` default without explicit user approval.
- On Apple Silicon, treat `llvm-tsan` failures that mention `/run/rosetta/rosetta` as the known emulation caveat, not as proof that the native Linux `amd64` lane is broken.
- Rebuild the image after changes to `docker-bake.hcl`, `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, `mise.toml`, `pixi.toml`, or `tooling/control_plane.py`.
- If you modify the build or lifecycle surfaces, re-run:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print dev_base >/tmp/cpp-devcontainer-dev-base.json
docker buildx bake -f docker-bake.hcl --print dev >/tmp/cpp-devcontainer-dev.json
python3 -m tooling validate --mode repo
```

## Outputs

Report:

- image tag and host username used
- whether `dev_base`, `cpp26_clang_core`, and `cpp26_gcc_core` were rebuilt or reused
- whether the macOS CLI path or an editor-managed path was used
- whether `post-create`, `ensure-devcontainer-ssh`, `smoke-ssh-git-gh-parity`, and host-local SSH smoke checks were run
- what secret path was assumed, if any (`mise.local.toml`, Doppler, or none)
