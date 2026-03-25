---
name: cpp-devcontainer-bake
description: Orchestrate this repository's host-aware devcontainer lifecycle around root `Dockerfile`, `docker-bake.hcl`, and `.devcontainer/devcontainer.json`. Use when building or rebuilding `cpp-devcontainer`, debugging username parity or SSH behavior, and inspecting Bake graph composition for `base`, `clang`, `gcc`, `final`, and `devcontainer`.
---

# C++ Devcontainer Bake

## Overview

Use this skill for the repo-specific devcontainer lifecycle. This is not a generic devcontainer generator.

## Load Order

1. Load `$python-pixi-astral-toolchain` for repo-owned Python, Pixi, uv, and mise policy.
2. Load `$pixi-devcontainer` for bootstrap and verification workflow details.

## Source Of Truth

- `Dockerfile` (root)
- `docker-bake.hcl`
- `.devcontainer/devcontainer.json`
- `README.md`
- `docs/latest-kernel-testing.md`

Read [references/repo-build-surface.md](references/repo-build-surface.md) before changing commands or explaining how the targets compose.
Read [references/docker-bake-guidance.md](references/docker-bake-guidance.md) when editing Bake semantics or explaining why the build graph exists.
Read [references/host-parity-and-bootstrap.md](references/host-parity-and-bootstrap.md) when the task touches host bootstrap, secrets, SSH, `gh`, or editor-vs-CLI devcontainer startup.

## Workflow

1. Use Bake as the default local build path:

```bash
docker buildx bake -f docker-bake.hcl devcontainer --load
```

2. Inspect the current Bake graph only when you need to explain or debug it:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print base
docker buildx bake -f docker-bake.hcl --print clang
docker buildx bake -f docker-bake.hcl --print gcc
docker buildx bake -f docker-bake.hcl --print final
docker buildx bake -f docker-bake.hcl --print devcontainer
```

3. After a successful host build, report the host-aware handoff:

```bash
docker image inspect cpp-devcontainer:dev >/dev/null
```

4. Inside the container, the checked-in lifecycle is:

```bash
uv run cpp-playground bootstrap finalize
uv run cpp-playground verify run
```

`postCreateCommand` and `postStartCommand` should only call the minimal runtime helper modules; do not add ad-hoc shell orchestration.

5. When the task touches SSH behavior, validate the checked-in parity contract:

```bash
uv run cpp-playground devcontainer smoke-ssh
```

On macOS hosts whose current shell does not export `SSH_AUTH_SOCK`, wrap host-side checks with:

```bash
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh-add -l
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh -T git@github.com
```

## Decision Rules

- Routine build or rebuild for local use: `docker buildx bake -f docker-bake.hcl devcontainer`
- Need to see resolved graph state before changing anything: `docker buildx bake --print <target>`
- Need to list the root groups and targets: `docker buildx bake --list=targets`
- Need post-build bootstrap or verify flows: `uv run cpp-playground bootstrap finalize`, `uv run cpp-playground verify run`
- Need Python-tooling policy questions: `$python-pixi-astral-toolchain`

## Guardrails

- Keep the root `Dockerfile` and `docker-bake.hcl` as the build graph.
- Do not generate `docker-compose.yml`, `setup.sh`, or README patterns from generic devcontainer templates for this repo.
- Do not recommend `remoteUser: root`; this repo requires `remoteUser=${localEnv:USER}` with `updateRemoteUserUID=true`.
- Do not bind-mount host `~/.claude`, `~/.codex`, `~/.gemini`, or host `~/.ssh`; this repo intentionally uses named volumes plus SSH-agent socket forwarding.
- On macOS with Docker Desktop, do not try to prove SSH parity by bind-mounting a host UNIX socket directly into the container. The supported design is a host-local TCP proxy plus the in-container UNIX socket `/tmp/cpp-playground-ssh-agent.sock`.
- Do not move host bootstrap into the container. `chezmoi` owns host shell/bootstrap state.
- Do not store long-lived tokens in `devcontainer.json`.
- Do not require `gh auth status` to pass inside the container as proof of SSH parity. Host `gh` auth may remain macOS-keychain-backed.
- Do not relax the repo's `linux/amd64` default without explicit user approval.
- On Apple Silicon, treat `llvm-tsan` failures that mention `/run/rosetta/rosetta` as the known emulation caveat, not as proof that the native Linux `amd64` lane is broken.
- Rebuild the image after changes to `Dockerfile`, `docker-bake.hcl`, or `.devcontainer/devcontainer.json`.
- If you modify the build or lifecycle surfaces, re-run:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print devcontainer >/tmp/cpp-devcontainer-dev.json
uv run cpp-playground verify run
```

## Outputs

Report:

- image tag and host username used
- whether `base`, `clang`, `gcc`, `final`, and `devcontainer` were rebuilt or reused
- whether runtime helper hooks were executed
- what host secret path was assumed, if any
- whether SSH parity was proven through matching agent identities and SSH-backed Git access
