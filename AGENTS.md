# AGENTS.md

## Scope
This is the repository-level instruction file for Codex runs in this repo.

## Apple Silicon Devcontainer Warning
- The checked-in devcontainer proof surface is Linux `amd64`, not Linux `arm64`.
- If you are running from an Apple Silicon host, do not assume Docker Desktop emulation is a valid proof surface for the repo's devcontainer verification path.
- If the `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and the process maps `/run/rosetta/rosetta`, treat that as the upstream emulation caveat tracked in issue `#1`, not as repo-local evidence that the native Linux `amd64` lane is broken.
- Do not broaden platform support or relax the proof bar without explicit user approval. Prefer a native Linux `amd64` Docker host or VM for authoritative devcontainer proof.

## Mac Devcontainer SSH Contract
- On macOS with Docker Desktop, do not assume a bind-mounted host UNIX socket is a usable SSH agent inside the Linux container. This repo's checked-in path is a host-local TCP proxy plus a container-local UNIX socket proxy.
- Keep `remoteEnv.SSH_AUTH_SOCK` aligned to the stable in-container socket path `/tmp/cpp-playground-ssh-agent.sock`.
- Treat SSH parity as "the container sees the same agent identities and can perform the same SSH-backed Git operations as the host." Do not require `gh auth status` parity, because host `gh` auth may be backed by the macOS keychain and intentionally not forwarded into the container.
- When validating host-side SSH behavior from macOS, prefer `SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ...` if the current shell does not already export `SSH_AUTH_SOCK`.
- Use `uv run cpp-playground devcontainer up --json` for the SSH-exposed runtime path. It defaults to host port `3333`, names the container as `cpp-playground-<devcontainer_user>-<ssh_port>`, and validates that SSH lands in the expected container.
- Override the default SSH port with `--ssh-port`, `CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT`, or a local `.devcontainer/devcontainer.env` file.
- `uv run cpp-playground devcontainer up` removes prior repo-owned devcontainer instances by default before launching the next one.
- Host SSH identities authenticate the connection, but the SSH username still selects the Linux account inside the container. Use `${USER}@127.0.0.1` when you want the explicit login target.
- Use `uv run cpp-playground devcontainer status --json` to retrieve the current SSH port, container name, container id, and workspace metadata for this repo.

## Multi-Agent Program
- The active repo workflow for multi-agent GitHub Actions remediation lives in:
  - `.agents/skills/gha-fix-loop/`
- Historical prompt/result artifacts are archived under:
  - `docs/agent-runs/`
- Historical plan review artifacts are archived under:
  - `docs/plan-reviews/`

## Multi-Agent Archival Contract
- Preserve earlier prompt/result/plan-review artifacts as historical records.
- Do not introduce new repo-owned operational content under `.codex/` beyond:
  - `.codex/config.toml`
  - `.codex/agents/*.toml`
- When durable run notes or review artifacts are needed, store them under `docs/`.

## Python Toolchain
- For Python, Pixi, uv, devcontainer, or `mise` work in this repo, prefer `$python-pixi-astral-toolchain` first:
  - `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/python-pixi-astral-toolchain/SKILL.md`
- For concrete Pixi, devcontainer, bootstrap, or verification workflow details, load `$pixi-devcontainer`:
  - `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md`
- Treat `uv`, `ruff`, and `ty` as one coordinated toolchain, not as optional independent tools.
- Treat `pixi` as the locked environment/task layer and `mise` as the exact fast-moving CLI pin layer.
- Prefer declarative repo-owned configuration in `pyproject.toml` or other checked-in config files over ad-hoc CLI flags.
- Keep linting, formatting, typing, dead code checks, duplication checks, modernization checks, and related static analysis enabled unless the user explicitly asks to relax policy.
- Use supplemental tools only for gaps Ruff does not cover well enough, and configure them declaratively.

## Automation Surface
- The canonical automation entrypoint is `cpp-playground`.
- Prefer:
  - `uv run cpp-playground bootstrap ...`
  - `uv run cpp-playground devcontainer ...`
  - `uv run cpp-playground image ...`
  - `uv run cpp-playground gha-fix-loop ...`
  - `uv run cpp-playground verify run`
- `install.sh` is the only checked-in shell bootstrap exception and must stay a thin trampoline into the Python CLI.
