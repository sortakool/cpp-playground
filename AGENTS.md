# AGENTS.md

## Scope
This is the repository-level instruction file for Codex runs in this repo.

## Apple Silicon Devcontainer Warning
- The checked-in devcontainer proof surface is Linux `amd64`, not Linux `arm64`.
- If you are running from an Apple Silicon host, do not assume Docker Desktop emulation is a valid proof surface for `pixi run prove-devcontainer`.
- If the `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and the process maps `/run/rosetta/rosetta`, treat that as the upstream emulation caveat tracked in issue `#1`, not as repo-local evidence that the native Linux `amd64` lane is broken.
- Do not broaden platform support or relax the proof bar without explicit user approval. Prefer a native Linux `amd64` Docker host or VM for authoritative devcontainer proof.

## Multi-Agent Program
- Multi-agent thread orchestration artifacts live in `.codex/multi-agent/`.
- Per-thread prompts live in `.codex/multi-agent/prompts/MA-*.md`.
- Thread outputs live in `.codex/multi-agent/results/MA-*-result.md`.

## Completion Contract (MA Threads)
- Every completed MA thread must produce a result file in `.codex/multi-agent/results/`.
- Result files must include these sections:
  - `## Findings`
  - `## Evidence Commands`
  - `## PASS/FAIL`
  - `## Blockers (Owner Thread)`
  - `## Learnings`
- After creating or updating a result file, run:
  - `./.codex/multi-agent/scripts/sync_agents_learnings.sh`

## Source of Truth
- Operational process and policy for MA threads is defined in:
  - `.codex/multi-agent/AGENTS.md`

## Python Toolchain
- For Python, Pixi, uv, devcontainer, `mise`, or `tooling/control_plane.py` work in this repo, prefer `$python-pixi-astral-toolchain` first:
  - `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/python-pixi-astral-toolchain/SKILL.md`
- For concrete Pixi, devcontainer, bootstrap, or `tooling/control_plane.py` workflow details, load `$pixi-devcontainer`:
  - `/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md`
- Treat `uv`, `ruff`, and `ty` as one coordinated toolchain, not as optional independent tools.
- Treat `pixi` as the locked environment/task layer and `mise` as the exact fast-moving CLI pin layer.
- Prefer declarative repo-owned configuration in `pyproject.toml` or other checked-in config files over ad-hoc CLI flags.
- Keep linting, formatting, typing, dead code checks, duplication checks, modernization checks, and related static analysis enabled unless the user explicitly asks to relax policy.
- Use supplemental tools only for gaps Ruff does not cover well enough, and configure them declaratively.
