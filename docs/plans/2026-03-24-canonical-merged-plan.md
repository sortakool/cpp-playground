# Canonical Merged Plan

This document is the active plan for the repository migration to:

- Codex-standard repo layout
- Python-only repo automation
- fast hosted devcontainer feedback with authoritative self-hosted validation

It supersedes the earlier draft plans and specs now archived under:

- [docs/archive/plans](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/archive/plans)
- [docs/archive/spec](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/archive/spec)
- [docs/plan-reviews](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plan-reviews)

## Canonical Direction

- `.codex/` is reserved for project-scoped Codex config only:
  - [`.codex/config.toml`](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/config.toml)
  - [`.codex/agents/`](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/agents)
- Repo skills live under [`.agents/skills/`](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills).
- Historical multi-agent outputs live under [docs/agent-runs](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/agent-runs).
- Historical plan-review artifacts live under [docs/plan-reviews](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plan-reviews).
- Repo-owned automation lives under [src/cpp_playground](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/src/cpp_playground) and is exposed through `cpp-playground`.
- `install.sh` remains the only checked-in shell exception and only trampolines into the Python CLI.
- The root [Dockerfile](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/Dockerfile) remains the single build graph with stages `base -> clang -> gcc -> final -> devcontainer`.
- Hosted CI builds fast feedback and publishes immutable `sha-*` candidates.
- Authoritative self-hosted validation pulls the published candidate and gates promotion of `:dev` or release tags.

## Retained Decisions

- Keep fast hosted CI for early feedback.
- Keep a slower authoritative self-hosted proof lane on `latest-kernel`.
- Publish immutable candidate images before moving rolling tags.
- Publish immutable `base`, `clang`, and `gcc` stage artifacts for cache reuse.
- Tighten the `final` bootstrap boundary so non-bootstrap repo edits do not rerun expensive bootstrap work.
- Keep `hk` as the only checked-in hook manager.
- Keep older plans/specs as archived records instead of deleting them.

## Active Interfaces

- `uv run cpp-playground bootstrap ...`
- `uv run cpp-playground devcontainer ...`
- `uv run cpp-playground image ...`
- `uv run cpp-playground gha-fix-loop ...`
- `uv run cpp-playground verify run`

## Archive Note

Earlier plan and spec documents are preserved for historical context only. When those documents disagree with current repo state, this plan and the checked-in code/config win.
