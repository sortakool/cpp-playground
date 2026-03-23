# `chezmoi` + `mise` + Devcontainer Migration Plan

This file is the canonical input to the Phase 0 adversarial review gate.

## Summary

- Run a non-mutating adversarial review on this migration plan before any repo PRs.
- Use the pinned local `claude` and `gemini` CLIs for execution.
- Use external skills only as review rubrics, not as required repo dependencies.
- Keep `chezmoi` host-scoped, `mise` public, and `pixi` responsible for locked helper environments.

## Phase 0 Review Gate

- Review this plan, not the codebase implementation work.
- Use these locked migration constraints:
  - true `chezmoi` source tree rooted at `home/` via `.chezmoiroot`
  - no overlap between `chezmoi` and repo-generated files owned by `tooling/templates/*`
  - `mise` as the public task and tool entrypoint
  - `pixi` retained for solved compiler and helper environments
- Claude pass:
  - review as a skeptical senior architect
  - focus on duplication boundaries, sequencing errors, rollback gaps, hidden maintenance cost, and simpler alternatives
- Gemini pass:
  - review as an independent adversarial reviewer
  - focus on repo-wide consistency, missing validation, and cross-checking against the current devcontainer and control-plane setup
- Cross-examination:
  - Claude must disposition Gemini findings as `agree`, `partially agree`, or `reject`
  - Gemini must disposition Claude findings as `agree`, `partially agree`, or `reject`
- Optional escalation:
  - run a committee-style arbitration pass only if the initial reviewers disagree on a high-impact item
- Required output:
  - `Accepted Findings`
  - `Rejected Findings`
  - `Open Risks`
  - `Required Plan Changes`

## PR Sequence

### PR 1

- Lock the architecture contract.
- Enforce the single-owner templating boundary between `chezmoi` and repo-generated surfaces.

### PR 2

- Introduce the true `chezmoi` source tree:
  - repo root: `.chezmoiroot`, `.chezmoiversion`
  - source state under `home/`
  - `home/.chezmoi.toml.tmpl`
  - `home/.chezmoiscripts/`

### PR 3

- Make `mise` the only documented public interface for repo tasks and CLI installs.
- Keep `pixi` tasks as compatibility shims while docs and control-plane messaging move to `mise run ...`.

### PR 4

- Keep the existing Docker/Bake graph and host-short-username devcontainer model.
- Continue refactoring the devcontainer toward a `mise`-first bootstrap path without weakening the Linux `amd64` proof surface.

### PR 5

- Narrow `pixi` to environment solving and helper lanes.
- Keep compiler and helper execution on `pixi run -e <env> ...`.

### PR 6

- Add repo validation that catches `chezmoi` layout drift and any attempt to manage repo-generated files from the `home/` source tree.

## Validation

- `mise run review-plan-phase0-dry-run`
- `mise run review-plan-phase0`
- `mise run validate-repo`
- `mise run validate-runtime`
- `mise run validate-all`
- `mise run prove-devcontainer`

## Assumptions

- `skills.sh` and `npx skills` remain the installability source of truth for external skill discovery.
- `skillfish` remains useful for discovery, but it is not part of the required repo workflow.
- The repo already pins `claude-code` and `gemini-cli`, so the review gate should use those CLIs directly.
