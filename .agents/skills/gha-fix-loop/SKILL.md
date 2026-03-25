---
name: gha-fix-loop
description: Trigger, monitor, and remediate GitHub Actions workflow failures in a closed loop using a specialized multi-agent SDLC team. Use when a GitHub Actions workflow or PR check should be dispatched or re-run, watched until completion, fixed after failures, and hardened with tests, docs, rules, AGENTS.md updates, or skill/process guardrails so the same class of issue is less likely to recur.
---

# GHA Fix Loop

## Overview

Use this skill for workflow-dispatch and CI-remediation loops, not for one-off
manual log inspection.

Follow the standard Codex Agent Skills layout:

- keep the reusable skill in `.agents/skills/<skill-name>/`
- keep the skill itself lean: `SKILL.md`, `agents/openai.yaml`,
  focused `references/`, and reusable `assets/` only when needed
- use `AGENTS.md` or nested `AGENTS.override.md` for project instructions
- use `.codex/config.toml` only for project-scoped Codex config, not as a skill
  or workflow-artifact directory

Keep this file lean, use the repo CLI for deterministic workflow polling, and
load focused references only when needed.

## Prerequisites

1. Verify `gh` authentication before relying on workflow commands.
2. Confirm the target repository, workflow, and ref or branch.
3. Prefer a branch with committed changes before triggering expensive reruns.

## Bundled Resources

- Agent topology and role split:
  [references/agent-topology.md](references/agent-topology.md)
- Required hardening and process-prevention pass:
  [references/hardening-checklist.md](references/hardening-checklist.md)

## Workflow

1. Establish the target run surface.
   - If the user wants a new run, dispatch the workflow.
   - If the user wants an existing run investigated, attach by `run_id`.
   - If the failure is on PR checks, use `$gh-fix-ci` for deeper failing-log
     extraction once the run is identified.
2. Start monitoring with:

```bash
uv run cpp-playground gha-fix-loop workflow-run --repo . --workflow <workflow-name-or-file> --ref <branch> --trigger
```

   Or attach to an existing run:

```bash
uv run cpp-playground gha-fix-loop workflow-run --repo . --run-id <run-id>
```

For local orchestration checks without GitHub access, use:

```bash
uv run cpp-playground gha-fix-loop workflow-run --repo . --workflow <workflow-name-or-file> --ref <branch> --trigger --dry-run
```

3. If the workflow passes, stop and report the run URL plus the validation
   surface it covered.
4. If the workflow fails, create a bounded SDLC subagent team.
5. Reproduce the failure locally before patching when practical.
6. Implement the minimum code fix plus one prevention artifact.
7. Re-run local validation, then re-dispatch or re-run the workflow.
8. Repeat until green or clearly blocked.

## Multi-Agent Team

Spawn only the smallest team that materially helps.

Default team:

- `lead` (main thread): owns run state, integration, and final decisions
- `explorer`: narrows the failing surface, maps files, and identifies likely
  root cause
- `worker`: implements the code or config fix
- `worker`: implements the prevention pass: tests, docs, AGENTS, rules, skills,
  scripts, or CI guardrails
- `reviewer`: checks that the remediation and prevention changes are correct and
  proportionate

Load [references/agent-topology.md](references/agent-topology.md) before
spawning agents.

If the issue touches a specialized area, load the relevant repo or global skill
before dispatching that worker. Examples:

- Python or tooling changes: `$python-pixi-astral-toolchain`
- CI failure log analysis on PR checks: `$gh-fix-ci`
- Documentation updates: `$update-docs`
- Security-sensitive paths: `$security-review`

If the remediation is large, cross-cutting, or expected to span multiple turns,
keep durable artifacts in standard repo locations such as:

- tracked documentation under `docs/`
- project instructions in `AGENTS.md`
- helper automation in `src/cpp_playground/`
- ordinary repo files under a clearly named tracked directory when persistent
  outputs are needed

## Hardening Rule

Every resolved issue must include at least one prevention artifact unless there
is a concrete reason it cannot.

Allowed prevention artifacts include:

- a regression test
- stricter lint, type, or static-analysis coverage
- a workflow or gate adjustment
- a scriptable verification step
- an AGENTS.md instruction
- a repo-local skill update
- documentation or runbook updates
- a guardrail in config or automation

Read [references/hardening-checklist.md](references/hardening-checklist.md)
before closing the loop.

## Output Contract

Report the result in this order:

1. workflow run summary: workflow, ref, run id, URL, final conclusion
2. root cause summary
3. code or config remediation
4. prevention artifacts added
5. local validation performed
6. rerun result or blocker

## Notes

- Do not stop after the first code fix if the workflow is still red.
- Do not treat docs-only changes as sufficient when a regression test or guard
  is feasible.
- Do not broaden the team unnecessarily; add agents only when they have a
  disjoint role.
