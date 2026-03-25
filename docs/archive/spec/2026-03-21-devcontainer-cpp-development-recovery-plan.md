# Superseded

This archived spec is superseded by [docs/plans/2026-03-24-canonical-merged-plan.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plans/2026-03-24-canonical-merged-plan.md).

# Devcontainer C++ Development Recovery Plan

> This file is the only execution spec for the follow-up implementation session. Do not re-plan the work. Execute this spec exactly, and only interview the human when this spec explicitly requires it.

**Goal:** Recover the repo's devcontainer-driven C++ development workflow end to end, with the devcontainer as the primary execution surface after image build succeeds, while preserving existing working validation behavior and avoiding any new tech debt.

**Architecture:** Use a code-and-docs-first recovery loop. First inspect the current repo state, tool code, official docs, and existing repo documentation; then reproduce failures; then apply only minimal source-of-truth patches; then re-sync generated artifacts through the control plane; then rebuild/recreate the devcontainer and rerun the exact verification sequence from a clean container. Persistence across restart and recreate is part of the required proof, not an optional follow-up.

**Tech Stack:** `tooling/control_plane.py`, `tooling/tool-version-manifest.json`, `tooling/templates/`, `tooling/cpp26-dev-images/`, `.devcontainer/`, `pixi`, `uv`, `ruff`, `ty`, `mise`, Docker Buildx, repo docs and CI workflows.

---

## Mission Boundaries

- Implement the recovery work end to end in the later session.
- Do not treat this as a greenfield redesign.
- Preserve all currently working validation behavior.
- Do not weaken checks, hide warnings, suppress errors, or add bypasses.
- Do not manually patch generated files.
- Do not assume any issue is pre-existing without evidence.
- Do not skip any warning, error, or issue, even if a command exits `0`.
- If uncertainty affects runtime behavior, policy, persistence, or developer workflow, interview the human before changing behavior.

## Immutable Operating Rules

1. Do not introduce tech debt.
2. Do not skip any warning, error, or issue.
3. Do not assume an issue was pre-existing without evidence from repo history, CI evidence, prior docs/specs, or official upstream documentation/issues.
4. If unsure and the ambiguity affects behavior, interview the human before changing behavior.
5. Always review the tool's code, official documentation, and repo implementation before changing behavior.
6. Always perform a gap analysis from current repo state to documented behavior and modern best-practice projects before changing behavior.
7. Treat the devcontainer as the primary execution surface immediately after `pixi run build-devcontainer-image` succeeds.
8. Preserve existing working validation behavior. A fix is invalid if it regresses a previously passing validation path.
9. Generated files must be re-synced through the control plane, never patched manually.
10. If the repo does not already expose a safe control-plane sync path for generated files without changing upstream version pins, implement that smallest safe control-plane sync path first, then use it. Do not misuse `pixi run refresh` for ordinary regeneration unless the intended fix is specifically to refresh upstream versions.

## Required Skill Load Order

Load these skills in this exact order before doing implementation work:

1. [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/python-pixi-astral-toolchain/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/python-pixi-astral-toolchain/SKILL.md)
2. [/Users/rmanaloto/.codex/skills/python-pixi-astral-toolchain/SKILL.md](/Users/rmanaloto/.codex/skills/python-pixi-astral-toolchain/SKILL.md)
3. [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/pixi-devcontainer/SKILL.md)
4. [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/cpp26-dev-image-build/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/cpp26-dev-image-build/SKILL.md)
5. [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/cpp26-dev-image-validate/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/cpp26-dev-image-validate/SKILL.md)
6. [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/ruff/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills/ruff/SKILL.md)
7. [/Users/rmanaloto/.codex/skills/astral-ty/SKILL.md](/Users/rmanaloto/.codex/skills/astral-ty/SKILL.md)
8. [/Users/rmanaloto/.codex/skills/uv-package-manager/SKILL.md](/Users/rmanaloto/.codex/skills/uv-package-manager/SKILL.md)
9. [/Users/rmanaloto/.codex/skills/verification-before-completion/SKILL.md](/Users/rmanaloto/.codex/skills/verification-before-completion/SKILL.md)

Optional only after a concrete failure is reproduced:

10. [/Users/rmanaloto/.codex/skills/systematic-debugging/SKILL.md](/Users/rmanaloto/.codex/skills/systematic-debugging/SKILL.md)

Do not change the load order. Do not skip a required skill. Do not load skill 10 before a concrete failure is reproduced.

## Mandatory Evidence Review Before Any Behavior Change

Before editing any file, complete and record a gap analysis based on all four sources below:

1. Current repo implementation
2. Tool code
3. Official documentation and release pages
4. Modern best-practice reference implementations

Review, at minimum, these repo files before changing behavior:

- [spec/2026-03-21-devcontainer-toolchain-verification-plan.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/spec/2026-03-21-devcontainer-toolchain-verification-plan.md)
- [README.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md)
- [AGENTS.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/AGENTS.md)
- [docs/latest-kernel-testing.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/latest-kernel-testing.md)
- [docs/mac-devcontainer-parity.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/mac-devcontainer-parity.md)
- [tooling/tool-version-manifest.json](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/tool-version-manifest.json)
- [tooling/templates/README.md.tmpl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/README.md.tmpl)
- [tooling/templates/pixi.toml.tmpl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/pixi.toml.tmpl)
- [.devcontainer/devcontainer.json](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/devcontainer.json)
- [.devcontainer/Dockerfile](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/Dockerfile)
- [docker-bake.hcl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docker-bake.hcl)
- [tooling/cpp26-dev-images/Dockerfile.clang-p2996](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/cpp26-dev-images/Dockerfile.clang-p2996)
- [tooling/cpp26-dev-images/Dockerfile.clang-p2996-quantlib](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/cpp26-dev-images/Dockerfile.clang-p2996-quantlib)
- [tooling/cpp26-dev-images/Dockerfile.gcc-reflection](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/cpp26-dev-images/Dockerfile.gcc-reflection)
- [tooling/control_plane.py](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/control_plane.py)
- [pixi.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml)
- [pyproject.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pyproject.toml)
- [.github/workflows/tooling-validate.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/tooling-validate.yml)

For every tool or behavior being changed, review:

- the relevant implementation in repo code
- the relevant official documentation
- the relevant official release notes or release page when version- or behavior-sensitive
- at least one modern best-practice example or official recommended workflow

The gap analysis must explicitly compare:

- current repo state
- documented repo state
- official documented behavior
- modern best-practice behavior
- intended fix
- reason the intended fix is the minimal correct fix

Do not patch first and analyze later.

## Allowed Optional Subagents

Subagents are allowed only within the constraints below. If no concrete failure or evidence gap justifies a subagent, do not use one.

### Image Build Investigator

- Allowed only after a concrete build, bootstrap, runtime, or image-related failure is reproduced.
- Required skills: 1-5 and 9, plus 10 only after failure reproduction.
- Scope: [tooling/control_plane.py](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/control_plane.py), [tooling/tool-version-manifest.json](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/tool-version-manifest.json), [tooling/templates/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/), [tooling/cpp26-dev-images/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/cpp26-dev-images/), [.devcontainer/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/)
- Deliverable: exact failing command, exact root cause, exact minimal patch proposal, exact verification command list
- Result file path: [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/MA-devcontainer-recovery-image-build-investigator-result.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/MA-devcontainer-recovery-image-build-investigator-result.md)

### Docs And Best-Practices Gap Analyst

- Allowed only when the owner thread needs documented-state or best-practice evidence to decide between multiple otherwise-plausible fixes, or when a narrow upstream caveat may need documentation instead of behavior change.
- Required skills: 1-3 and 9
- Scope: [README.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md), [AGENTS.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/AGENTS.md), [docs/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/), CI workflows, official tool docs/release pages referenced by the code
- Deliverable: gap table of current state vs documented state vs best practice, with no code changes
- Result file path: [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/MA-devcontainer-recovery-docs-gap-analyst-result.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/MA-devcontainer-recovery-docs-gap-analyst-result.md)

### Required Subagent Result Schema

If any subagent is used, its result file must be written under:

- [/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.codex/multi-agent/results/)

Every subagent result file must include these sections exactly:

- `## Findings`
- `## Evidence Commands`
- `## PASS/FAIL`
- `## Blockers (Owner Thread)`
- `## Learnings`

After creating or updating a subagent result file, run:

```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

The owner thread remains responsible for all final decisions. A subagent result is evidence, not authorization to patch blindly.

## Exact Execution Sequence

### Phase 0: Baseline Guardrails

1. Work from the current branch/worktree state; do not discard unrelated user changes.
2. Record the starting dirty-state evidence with `git status --short`.
3. Do not change behavior before the mandatory review and gap analysis are complete.
4. Do not run repo validation or prove flows on the host except for building the devcontainer image and host-only actions required to open or recreate the devcontainer.

### Phase 1: Host-Side Inspection And Image Build

1. Complete the mandatory review and gap analysis.
2. Build the wrapper devcontainer image on the host:

```bash
pixi run build-devcontainer-image
```

3. If the image build fails:
   - capture the exact failing command and logs
   - reproduce the same failure once
   - only then optionally load skill 10
   - only then optionally use the `Image Build Investigator` subagent
   - do not move primary execution to the host; fix only what is necessary to make the image build succeed
4. Once the image build succeeds, the devcontainer becomes the primary execution surface for the rest of the work.

### Phase 2: Enter The Devcontainer

1. Open the repo in the devcontainer built from the current repo state.
2. Confirm you are inside the devcontainer and on the expected execution surface:

```bash
pwd
uname -m
python3 --version
pixi --version
uv --version
mise --version
```

3. Create persistence probes before running the verification sequence:

```bash
workspace_probe=".git/devcontainer-workspace-persistence-probe"
mise_probe="$HOME/.local/share/mise/devcontainer-persistence-probe"
pixi_probe="$HOME/.pixi/devcontainer-persistence-probe"
printf 'workspace:%s\n' "$(date -u +%Y%m%dT%H%M%SZ)" > "$workspace_probe"
printf 'mise:%s\n' "$(date -u +%Y%m%dT%H%M%SZ)" > "$mise_probe"
printf 'pixi:%s\n' "$(date -u +%Y%m%dT%H%M%SZ)" > "$pixi_probe"
cat "$workspace_probe"
cat "$mise_probe"
cat "$pixi_probe"
```

These exact files are the required persistence evidence later:

- workspace content via `.git/devcontainer-workspace-persistence-probe`
- devcontainer-local state via `mise-home` at `$HOME/.local/share/mise/devcontainer-persistence-probe`
- devcontainer-local state via `pixi-home` at `$HOME/.pixi/devcontainer-persistence-probe`

### Phase 3: In-Devcontainer Verification Sequence

The in-devcontainer verification sequence is exactly the following commands, in exactly this order, with no reordering and no omissions:

1. `pixi run bootstrap`
2. `pixi run validate-repo`
3. `pixi run validate-runtime`
4. `pixi run validate-all`
5. `pixi run ruff-check`
6. `pixi run ruff-format`
7. `pixi run ty-check`
8. `uv run ruff check tooling`
9. `uv run ruff format --check tooling`
10. `uv run ty check tooling`
11. `mise install --locked`
12. `mise lock`
13. `pixi run prove-devcontainer`

## Failure-Handling And Escalation Rules

Apply these rules every time a command warns, errors, or fails:

1. Capture the exact command, exit code, stderr, warnings, and relevant log tail.
2. Reproduce the same issue once before changing code.
3. Only after concrete reproduction may you load skill 10.
4. Before patching, review:
   - the relevant repo code
   - the relevant official docs/release notes
   - the relevant repo docs/CI behavior
   - the current gap analysis
5. Classify the issue into one or more of:
   - image build failure
   - devcontainer runtime drift
   - control-plane bug
   - generated-file drift
   - repo docs/CI drift
   - `mise` isolation behavior mismatch
   - upstream tool caveat
   - pre-existing issue with evidence
6. Never label an issue pre-existing without evidence. Acceptable evidence includes:
   - prior failing CI or committed issue history
   - prior spec/doc text proving the mismatch pre-dated the session
   - official upstream issue or release note proving the observed behavior is external
7. If more than one fix is defensible and the choice changes behavior, interview the human before editing.
8. If generated files need to change:
   - modify only the source-of-truth inputs first
   - re-sync via the control plane
   - never hand-edit generated outputs
9. If the repo lacks a safe sync-only control-plane entry point, implement the smallest correct one first and use it immediately after.
10. Do not broaden the fix beyond the reproduced root cause.
11. Do not ignore warnings. If a warning is benign, prove why with code and documentation evidence, then either eliminate it or document it narrowly if it is true upstream behavior.
12. Preserve existing working validation behavior. If a previously green command turns red after your patch, that is a regression and must be fixed before completion.

## Patch Rules

1. Prefer fixing source-of-truth files over generated outputs.
2. Prefer minimal local fixes over policy changes.
3. Do not float versions, add TODOs, add bypass flags, or weaken checks.
4. Do not remove validations to make the sequence pass.
5. If you touch any generated-output source, immediately re-sync through the control plane and re-run `pixi run validate-repo`.
6. If you touch any of the following, rebuild the devcontainer image and recreate the devcontainer before final verification:
   - [tooling/control_plane.py](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/control_plane.py)
   - [tooling/tool-version-manifest.json](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/tool-version-manifest.json)
   - anything under [tooling/templates/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/templates/)
   - anything under [tooling/cpp26-dev-images/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/tooling/cpp26-dev-images/)
   - anything under [.devcontainer/](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/)
   - [pixi.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml)
   - [pyproject.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pyproject.toml)

## Exact Reverification Rules

### After Each Fix

1. Re-run the exact failing command first.
2. Re-run any immediately dependent validation command next.
3. If the fix touched image, devcontainer, control-plane, template, lockfile, or tooling policy files, then:
   - rebuild the image with `pixi run build-devcontainer-image`
   - recreate the devcontainer
   - restart the verification sequence from step 1

### Final Verification Pass

Completion requires a clean final verification pass from a fresh recreated devcontainer:

1. Build the image again on the host:

```bash
pixi run build-devcontainer-image
```

2. Recreate the devcontainer from the current repo state.
3. Before rerunning the 13-command sequence, verify persistence probes survived recreate:

```bash
cat .git/devcontainer-workspace-persistence-probe
cat "$HOME/.local/share/mise/devcontainer-persistence-probe"
cat "$HOME/.pixi/devcontainer-persistence-probe"
```

4. Rerun the full 13-command in-devcontainer verification sequence from step 1 through step 13 exactly as listed.

## Required Persistence Verification

Persistence verification is mandatory and must cover both restart and recreate.

### Restart Verification

After you have one full passing verification sequence in a running devcontainer, restart that devcontainer without deleting it. Then run:

```bash
cat .git/devcontainer-workspace-persistence-probe
cat "$HOME/.local/share/mise/devcontainer-persistence-probe"
cat "$HOME/.pixi/devcontainer-persistence-probe"
```

Required outcome:

- the workspace probe still exists and contains the original value
- the `mise-home` probe still exists and contains the original value
- the `pixi-home` probe still exists and contains the original value

### Recreate Verification

After restart verification passes, recreate the devcontainer and run the same three `cat` commands again before the final verification sequence.

Required outcome:

- workspace content persists across recreate
- named-volume devcontainer-local state persists across recreate

If restart or recreate persistence fails, treat that as a blocking defect and recover it before completion.

## `mise` Isolation Decision Rule

The implementation session must explicitly determine which of the following is true:

1. `mise` isolation is fully working in-container.
2. `mise` isolation is not fully working in-container, but the remaining caveat is a narrow upstream behavior that is correctly documented.
3. `mise` isolation is blocked.

This determination is mandatory. Do not leave it implicit.

The determination must be based on:

- repo control-plane code and behavior
- direct in-container `mise install --locked` and `mise lock` behavior
- official `mise` docs and release behavior
- current repo docs and CI expectations

Do not silently relax the repo isolation policy to match upstream defaults.

## Acceptance Criteria

The work is complete only if all of the following are true:

1. The required skills were loaded in the exact required order.
2. The mandatory review and gap analysis were completed before behavior changes.
3. The wrapper devcontainer image builds successfully from the current repo state.
4. Once image build succeeds, the devcontainer was used as the primary execution surface.
5. The exact 13-command in-devcontainer verification sequence passes in order from a fresh recreated devcontainer.
6. Existing working validation behavior is preserved.
7. No warning, error, or issue was skipped.
8. No generated file was patched manually; generated outputs were re-synced through the control plane.
9. Workspace-content persistence across devcontainer restart and recreate was proven.
10. Devcontainer-local state persistence via named volume(s) across devcontainer restart and recreate was proven.
11. `pixi run prove-devcontainer` is green at the end.
12. The final `mise` isolation status is explicitly one of:
    - fully working
    - narrowly documented upstream behavior
    - blocked
13. Any remaining caveat is narrow, evidenced, documented, and does not rely on hand-waving.
14. The final diff is minimal and free of new tech debt.

## Required Final Implementation Report Format

The final implementation session report must contain exactly these nine sections, in this exact order, with these exact headings:

```markdown
## 1. Gap analysis summary from current state to documented and best-practice state
## 2. Which verification commands passed unchanged
## 3. Which commands failed initially
## 4. Which warnings/errors/issues were encountered and how each was resolved
## 5. What minimal patches were required
## 6. Whether `pixi run prove-devcontainer` remained green
## 7. Whether the `mise` isolation policy is fully working, narrowly documented as upstream behavior, or blocked
## 8. Which skills were loaded, in exact order
## 9. Whether any subagent was used, with result file paths
```

Do not add extra numbered sections. If the human asks for more detail, provide it after these nine sections.

## Completion Notes

- Reuse the existing verified context in this repo; do not restart from scratch.
- This is an execution-and-recovery session, not a brainstorming session.
- Prefer minimal, source-of-truth, policy-compliant patches.
- Evidence before assertions.
