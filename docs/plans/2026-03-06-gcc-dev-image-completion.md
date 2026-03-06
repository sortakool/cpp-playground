# GCC Dev Image Completion (MA-10..MA-12) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finish the remaining GCC readiness work by building and validating `cpp26-dev-gcc:dev` and proving final acceptance with `--require-gcc`.

**Architecture:** Add a focused follow-up MA wave (`MA-10..MA-12`) rather than rewriting MA-06/07 outcomes. Reuse existing build/validate/gate scripts and keep scope narrow to GCC core only. Each thread must produce reproducible evidence, binary PASS/FAIL, and commit artifacts.

**Tech Stack:** Bash, Docker/buildx, `.codex/multi-agent/*` prompt/result framework, `.agents/skills/cpp26-dev-image-build/scripts/build_images.sh`, `.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh`, `.codex/multi-agent/scripts/ma_dev_image_gate.sh`.

---

## Save Location
Save this plan as:

`docs/plans/2026-03-06-gcc-dev-image-completion.md`

---

### Task 1: Establish GCC Gap Baseline

**Files:**
- Test: `.codex/multi-agent/results/MA-06-result.md`
- Test: `.codex/multi-agent/results/MA-07-result.md`
- Test: `.codex/multi-agent/results/MA-09-result.md`

**Step 1: Write the failing test**

```bash
docker image inspect cpp26-dev-gcc:dev >/dev/null 2>&1; echo "gcc_image_exit=$?"
```

Expected: `gcc_image_exit=1` (currently missing) before implementation starts.

**Step 2: Run test to verify it fails**

Run:
```bash
docker image inspect cpp26-dev-gcc:dev >/dev/null 2>&1; echo "gcc_image_exit=$?"
```

Expected: exit code indicates missing GCC image.

**Step 3: Write minimal implementation**

No code changes in this task. Capture baseline evidence commands and outputs in task notes for MA-10 kickoff.

**Step 4: Run test to verify it passes**

Run:
```bash
rg -n "optional gcc|optional skip|--require-gcc not set" .codex/multi-agent/results/MA-06-result.md .codex/multi-agent/results/MA-07-result.md .codex/multi-agent/results/MA-09-result.md
```

Expected: evidence confirms GCC was previously optional/skipped.

**Step 5: Commit**

No commit for Task 1 (read-only baseline).

---

### Task 2: Add MA-10..MA-12 Thread Definitions and Prompts

**Files:**
- Modify: `.codex/multi-agent/THREADS.md`
- Create: `.codex/multi-agent/prompts/MA-10.md`
- Create: `.codex/multi-agent/prompts/MA-11.md`
- Create: `.codex/multi-agent/prompts/MA-12.md`
- Modify: `.codex/multi-agent/AGENTS.md`

**Step 1: Write the failing test**

```bash
for f in 10 11 12; do test -f ".codex/multi-agent/prompts/MA-${f}.md" || echo "missing MA-${f}"; done
rg -n "MA-10|MA-11|MA-12" .codex/multi-agent/THREADS.md
```

Expected: prompts missing and no thread entries yet.

**Step 2: Run test to verify it fails**

Run command above.  
Expected: missing files/entries.

**Step 3: Write minimal implementation**

Implement:
- `MA-10.md` (Build GCC Core Dev Image)
  - Required path:
    - `./.agents/skills/cpp26-dev-image-build/scripts/build_images.sh --toolchain gcc --flavor core --image-tag dev`
  - Required result file:
    - `.codex/multi-agent/results/MA-10-result.md`
  - Required sections and commit evidence.
- `MA-11.md` (Validate GCC Core Dev Image)
  - Required path:
    - `./.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain gcc --flavor core --image-tag dev`
  - Required result file:
    - `.codex/multi-agent/results/MA-11-result.md`
  - Required sections and commit evidence.
- `MA-12.md` (Final GCC Acceptance)
  - Required path:
    - `./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc`
  - Required result file:
    - `.codex/multi-agent/results/MA-12-result.md`
  - Required sections and commit evidence.
- Update `.codex/multi-agent/THREADS.md` with MA-10..12 order after MA-09.
- Update `.codex/multi-agent/AGENTS.md` policy note: MA-10..12 must include telemetry/log evidence and strict gate evidence.

**Step 4: Run test to verify it passes**

```bash
for f in 10 11 12; do test -f ".codex/multi-agent/prompts/MA-${f}.md"; done
rg -n "MA-10|MA-11|MA-12" .codex/multi-agent/THREADS.md .codex/multi-agent/AGENTS.md
rg -n "results/MA-1[0-2]-result.md|## Findings|## Evidence Commands|## PASS/FAIL|## Blockers \\(Owner Thread\\)|## Learnings" .codex/multi-agent/prompts/MA-1*.md
```

Expected: all checks pass.

**Step 5: Commit**

```bash
git add .codex/multi-agent/THREADS.md .codex/multi-agent/AGENTS.md .codex/multi-agent/prompts/MA-10.md .codex/multi-agent/prompts/MA-11.md .codex/multi-agent/prompts/MA-12.md
git commit -m "ma: add MA-10..MA-12 gcc completion threads"
```

---

### Task 3: Execute MA-10 (Build GCC Core)

**Files:**
- Create: `.codex/multi-agent/results/MA-10-result.md`
- Modify: `.codex/multi-agent/AGENTS.md` (auto-learnings via sync)

**Step 1: Write the failing test**

```bash
docker image inspect cpp26-dev-gcc:dev >/dev/null 2>&1; echo "pre_build_exit=$?"
```

Expected: `pre_build_exit=1`.

**Step 2: Run test to verify it fails**

Run the command above.  
Expected: missing image before build.

**Step 3: Write minimal implementation**

Run MA-10 required command:
```bash
./.agents/skills/cpp26-dev-image-build/scripts/build_images.sh --toolchain gcc --flavor core --image-tag dev
```

Then:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
./.codex/scripts/strict_multi_agent_gate.sh
```

Write `.codex/multi-agent/results/MA-10-result.md` with required sections and exact evidence commands.

**Step 4: Run test to verify it passes**

```bash
docker image inspect cpp26-dev-gcc:dev >/dev/null 2>&1; echo "post_build_exit=$?"
```

Expected: `post_build_exit=0`.

**Step 5: Commit**

```bash
git add .codex/multi-agent/results/MA-10-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-10 build gcc core dev image"
git show --name-only --oneline -n 1
```

---

### Task 4: Execute MA-11 (Validate GCC Core)

**Files:**
- Create: `.codex/multi-agent/results/MA-11-result.md`
- Modify: `.codex/multi-agent/AGENTS.md` (auto-learnings via sync)

**Step 1: Write the failing test**

```bash
./.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain gcc --flavor core --image-tag dev --dry-run
```

Expected: dry-run command composition verified before real validation.

**Step 2: Run test to verify it fails**

Run real validation and confirm there is no prior PASS evidence file:
```bash
test -f .codex/multi-agent/results/MA-11-result.md && echo "already_exists" || echo "missing_result"
```

Expected: `missing_result`.

**Step 3: Write minimal implementation**

Run:
```bash
./.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain gcc --flavor core --image-tag dev | tee /tmp/ma11-validate-gcc.log
./.codex/multi-agent/scripts/sync_agents_learnings.sh
./.codex/scripts/strict_multi_agent_gate.sh
```

Write `.codex/multi-agent/results/MA-11-result.md` with required sections and exact evidence commands.

**Step 4: Run test to verify it passes**

```bash
tail -n 40 /tmp/ma11-validate-gcc.log
```

Expected: summary shows all selected GCC checks passed.

**Step 5: Commit**

```bash
git add .codex/multi-agent/results/MA-11-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-11 validate gcc core dev image"
git show --name-only --oneline -n 1
```

---

### Task 5: Execute MA-12 (Final GCC Acceptance)

**Files:**
- Create: `.codex/multi-agent/results/MA-12-result.md`
- Modify: `.codex/multi-agent/AGENTS.md` (auto-learnings via sync)

**Step 1: Write the failing test**

```bash
./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc | tee /tmp/ma12-gate.log
```

Expected: if any required GCC check fails, gate fails here (this is the pre-fix detector).

**Step 2: Run test to verify it fails**

Run command above once.  
Expected: fail only if environment still not ready; if it passes immediately, treat this as successful first run and proceed.

**Step 3: Write minimal implementation**

If failed:
- remediate only the specific failing check from gate output (no scope creep).
Then run:
```bash
./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc | tee /tmp/ma12-gate.log
./.codex/scripts/strict_multi_agent_gate.sh
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

Write `.codex/multi-agent/results/MA-12-result.md` with required sections and exact evidence commands.

**Step 4: Run test to verify it passes**

```bash
grep -n "DEV IMAGE GATE RESULT: PASS" /tmp/ma12-gate.log
```

Expected: PASS line present.

**Step 5: Commit**

```bash
git add .codex/multi-agent/results/MA-12-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-12 final gcc acceptance gate"
git show --name-only --oneline -n 1
```

---

### Task 6: Final Verification and Push

**Files:**
- Modify: none

**Step 1: Write the failing test**

```bash
git status --short
```

Expected: may show changes before final cleanup.

**Step 2: Run test to verify it fails**

Run:
```bash
./.codex/scripts/strict_multi_agent_gate.sh
./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc
```

Expected: both must PASS; if not, stop and fix blocker from output.

**Step 3: Write minimal implementation**

Ensure all MA-10..12 commits are present and working tree is clean.

**Step 4: Run test to verify it passes**

```bash
git status --short
git log --oneline -n 10
```

Expected: clean tree and visible MA-10..12 commits.

**Step 5: Commit + Push**

No extra commit unless required. Push:
```bash
git push origin main
```

---

## Required Quality Rules
- Use `@parallel-agents` and `@subagent-driven-development` patterns for thread execution.
- DRY/YAGNI: reuse existing build/validate/gate scripts; do not add new image pipelines.
- TDD style per task: failing check -> minimal change -> passing check.
- Frequent commits exactly as listed.
- Do not run quantlib or publish flows.

---

## Acceptance Criteria (Definition of Done)
- `cpp26-dev-gcc:dev` exists locally.
- GCC core validation passes.
- `./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc` passes.
- New prompts/results for MA-10..12 exist with required sections and evidence.
- Strict gate remains PASS.
- Branch clean and pushed to `origin/main`.
