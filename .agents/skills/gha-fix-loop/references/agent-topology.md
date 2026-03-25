# Agent Topology

Use a small, explicit team with disjoint responsibilities.

## Default Roles

- `lead`
  - keeps workflow state
  - decides when to re-run
  - integrates patches
  - rejects weak or duplicate findings
- `explorer`
  - inspects failing jobs and touched files
  - identifies likely root cause and reproduction path
  - should not edit code unless the task is intentionally merged
- `implementation-worker`
  - edits the code or workflow under failure
  - keeps changes narrowly scoped to the root cause
- `hardening-worker`
  - adds the prevention layer
  - updates tests, docs, AGENTS, skills, rules, scripts, or CI checks
  - should not merely restate the fix; it must make recurrence harder
- `reviewer`
  - verifies the claimed root cause and the adequacy of the prevention pass
  - checks for regressions, missing validation, and overfitting

## Optional Roles

- add a second `implementation-worker` only when write scopes are disjoint
- add a security-focused reviewer when auth, secrets, input handling, or
  privileged automation is involved
- archive durable prompts, reviews, or run notes under `docs/agent-runs/` when
  the issue is large enough to merit persistent artifacts

## Dispatch Rules

- Keep the immediate blocker local when the next action depends on it.
- Delegate sidecar work in parallel:
  - root-cause mapping
  - docs or AGENTS updates
  - prevention guardrails
  - reviewer verification
- Do not have multiple workers editing the same file set without a clear split.

## Completion Standard

The lead should not declare the loop complete until:

1. the failing workflow is green or a blocker is explicit
2. the root cause is stated concretely
3. at least one prevention artifact landed or was consciously waived
4. the reviewer has checked both the fix and the hardening pass
