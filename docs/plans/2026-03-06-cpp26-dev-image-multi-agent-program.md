# C++26 Dev Images MA-05..MA-09 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a new multi-agent execution wave (MA-05..MA-09) in Codex CLI to build and validate local development Docker images with telemetry-backed proof that orchestration is working.

**Architecture:** Extend the existing `.codex/multi-agent/` framework by adding new thread prompts/results plus two scripts: one telemetry evidence collector and one final dev-image acceptance gate. Reuse existing image build/validate skills and scripts; do not introduce new image pipelines. Every thread must produce reproducible evidence, PASS/FAIL, and commit artifacts.

**Tech Stack:** Bash, Docker/buildx, ripgrep, existing `.codex/multi-agent/*` docs/scripts, existing image skills in `.agents/skills/cpp26-dev-image-*`.

---

## Context Snapshot (Zero-Context Bootstrap)
- Existing MA framework is complete through MA-04.
- Source files already present:
  - `.codex/multi-agent/THREADS.md`
  - `.codex/multi-agent/AGENTS.md`
  - `.codex/multi-agent/SKILLS_TRIGGER_MATRIX.md`
  - `.codex/multi-agent/VALIDATION_GATE.md`
  - `.codex/scripts/strict_multi_agent_gate.sh`
- Existing image scripts already present:
  - `.agents/skills/cpp26-dev-image-build/scripts/build_images.sh`
  - `.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh`
  - `.agents/skills/cpp26-dev-image-publish/scripts/publish_images.sh` (not used in this phase)

---

## Scope Locks (Must Enforce)
- Required: `clang` core dev image (`cpp26-dev-clang:dev`) build + validation.
- Optional: `gcc` core dev image (`cpp26-dev-gcc:dev`) build + validation.
- Out of scope: `quantlib` flavor.
- Out of scope: publish/retag/push workflows.
- Execution mode: Codex CLI multi-agent orchestration.
- Result format: each MA thread must include:
  - `## Findings`
  - `## Evidence Commands`
  - `## PASS/FAIL`
  - `## Blockers (Owner Thread)`
  - `## Learnings`

---

## Implementation Tasks

### Task 1: Extend Thread Inventory + Policy for MA-05..MA-09
**Files**
- Modify: `.codex/multi-agent/THREADS.md`
- Modify: `.codex/multi-agent/AGENTS.md`

**What to implement**
- Add threads:
  - `MA-05 Environment + Team Bootstrap`
  - `MA-06 Build Core Dev Images`
  - `MA-07 Validate Core Dev Images`
  - `MA-08 Telemetry/Log Verification`
  - `MA-09 Final Dev Acceptance Gate`
- Add execution order and role ownership.
- Add policy note in `.codex/multi-agent/AGENTS.md` that MA-05+ requires telemetry/log evidence in each result.

**Verification**
```bash
rg -n "MA-05|MA-06|MA-07|MA-08|MA-09|telemetry|log evidence" .codex/multi-agent/THREADS.md .codex/multi-agent/AGENTS.md
```

**Commit**
```bash
git add .codex/multi-agent/THREADS.md .codex/multi-agent/AGENTS.md
git commit -m "ma: add MA-05..MA-09 inventory and telemetry policy"
```

---

### Task 2: Create Prompts MA-05..MA-09
**Files**
- Create: `.codex/multi-agent/prompts/MA-05.md`
- Create: `.codex/multi-agent/prompts/MA-06.md`
- Create: `.codex/multi-agent/prompts/MA-07.md`
- Create: `.codex/multi-agent/prompts/MA-08.md`
- Create: `.codex/multi-agent/prompts/MA-09.md`

**What to implement**
- MA-05: prerequisite and telemetry baseline bootstrap.
- MA-06: build images via build script (`--flavor core`, clang required, gcc optional).
- MA-07: validate via test script (`--flavor core`, clang required, gcc optional).
- MA-08: verify telemetry/log evidence for MA-05..MA-07 run windows.
- MA-09: run final binary gate and produce final PASS/FAIL with owner-thread remediation mapping.
- Each prompt must include:
  - required result sections
  - requirement to run thread validation commands before PASS/FAIL
  - requirement to run `.codex/multi-agent/scripts/sync_agents_learnings.sh`
  - PASS commit evidence commands and commit message pattern.

**Verification**
```bash
for f in 05 06 07 08 09; do
  test -f ".codex/multi-agent/prompts/MA-${f}.md" || exit 1
done
rg -n "results/MA-0[5-9]-result.md|## Findings|## Evidence Commands|## PASS/FAIL|## Blockers \\(Owner Thread\\)|## Learnings" .codex/multi-agent/prompts/MA-0*.md
```

**Commit**
```bash
git add .codex/multi-agent/prompts/MA-05.md .codex/multi-agent/prompts/MA-06.md .codex/multi-agent/prompts/MA-07.md .codex/multi-agent/prompts/MA-08.md .codex/multi-agent/prompts/MA-09.md
git commit -m "ma: add MA-05..MA-09 prompt specs"
```

---

### Task 3: Add Telemetry Collector Script
**Files**
- Create: `.codex/multi-agent/scripts/collect_thread_telemetry.sh`
- Modify: `.codex/multi-agent/VALIDATION_GATE.md`

**What to implement**
- Script arguments:
  - `--since <time>` required (e.g., `30m` or RFC3339)
  - `--until <time>` optional
  - `--collector <container>` optional, default `codex-otel-collector`
- Script output sections:
  - codex event lines
  - duplicated OTLP path error scan
  - retry/drop timeout scan for `internal_logs`/`internal_traces`
- Behavior:
  - Non-zero exit only for operational failures (e.g., collector inaccessible)
  - Zero exit for successful evidence extraction regardless of event volume.

**Verification**
```bash
bash -n .codex/multi-agent/scripts/collect_thread_telemetry.sh
chmod +x .codex/multi-agent/scripts/collect_thread_telemetry.sh
.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 30m | head -n 80
```

**Commit**
```bash
git add .codex/multi-agent/scripts/collect_thread_telemetry.sh .codex/multi-agent/VALIDATION_GATE.md
git commit -m "ma: add thread telemetry evidence script"
```

---

### Task 4: Add Final Dev Image Gate Script
**Files**
- Create: `.codex/multi-agent/scripts/ma_dev_image_gate.sh`
- Modify: `.codex/multi-agent/VALIDATION_GATE.md`

**What to implement**
- Gate checks (required):
  1. `./.codex/scripts/strict_multi_agent_gate.sh` passes
  2. `cpp26-dev-clang:dev` exists locally
  3. clang core validation passes:
     - `.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain clang --flavor core --image-tag dev`
  4. telemetry evidence is present and stable:
     - use `collect_thread_telemetry.sh --since 30m`
- Gate checks (optional path):
  - gcc core validation only when `--require-gcc` is passed; otherwise report optional skip.
- Output:
  - `PASS:` / `FAIL:` per check
  - final line: `DEV IMAGE GATE RESULT: PASS|FAIL`
- Exit non-zero on required check failure.

**Verification**
```bash
bash -n .codex/multi-agent/scripts/ma_dev_image_gate.sh
chmod +x .codex/multi-agent/scripts/ma_dev_image_gate.sh
.codex/multi-agent/scripts/ma_dev_image_gate.sh
```

**Commit**
```bash
git add .codex/multi-agent/scripts/ma_dev_image_gate.sh .codex/multi-agent/VALIDATION_GATE.md
git commit -m "ma: add final dev image acceptance gate"
```

---

### Task 5: Update Skill Trigger Matrix for New Wave
**Files**
- Modify: `.codex/multi-agent/SKILLS_TRIGGER_MATRIX.md`

**What to implement**
- Add intent rows for:
  - local-only dev image build/validate orchestration
  - telemetry verification thread
  - final dev acceptance gate
- Keep publish explicit-only unchanged.
- Add negative checks:
  - build/validate language must not trigger publish
  - quantlib requests are out-of-scope in this wave.

**Verification**
```bash
rg -n "local-only|telemetry|acceptance gate|explicit-only|quantlib.*out-of-scope" .codex/multi-agent/SKILLS_TRIGGER_MATRIX.md
```

**Commit**
```bash
git add .codex/multi-agent/SKILLS_TRIGGER_MATRIX.md
git commit -m "ma: extend trigger matrix for MA-05..MA-09"
```

---

### Task 6: Execute MA-05..MA-09 and Produce Result Artifacts
**Files**
- Create: `.codex/multi-agent/results/MA-05-result.md`
- Create: `.codex/multi-agent/results/MA-06-result.md`
- Create: `.codex/multi-agent/results/MA-07-result.md`
- Create: `.codex/multi-agent/results/MA-08-result.md`
- Create: `.codex/multi-agent/results/MA-09-result.md`
- Modify (auto-generated): `.codex/multi-agent/AGENTS.md` via sync script

**What to implement**
- Run each thread prompt in order with CLI multi-agent orchestration.
- Ensure each result includes exact evidence commands and binary PASS/FAIL.
- For MA-06/07, enforce scope locks:
  - clang required
  - gcc optional path clearly marked PASS or skipped with rationale
  - no quantlib/publish actions.
- After each result update:
  - run `./.codex/multi-agent/scripts/sync_agents_learnings.sh`
  - run required validation commands from prompt
  - commit on PASS with prompt-defined commit message.

**Verification**
```bash
for f in 05 06 07 08 09; do
  test -f ".codex/multi-agent/results/MA-${f}-result.md" || exit 1
  rg -n "^## Findings|^## Evidence Commands|^## PASS/FAIL|^## Blockers \\(Owner Thread\\)|^## Learnings" ".codex/multi-agent/results/MA-${f}-result.md"
done
```

---

### Task 7: Final Acceptance, Clean State, Push
**Files**
- Modify: none (verification/push)

**What to implement**
- Run final gates:
  - `./.codex/scripts/strict_multi_agent_gate.sh`
  - `./.codex/multi-agent/scripts/ma_dev_image_gate.sh`
- Verify clean tree.
- Push to remote.

**Verification**
```bash
git status --short
./.codex/scripts/strict_multi_agent_gate.sh
./.codex/multi-agent/scripts/ma_dev_image_gate.sh
git status --short
```

Expected:
- both gates PASS
- clean working tree

**Push**
```bash
git push origin main
```

---

## Required Quality Rules
- TDD for each new script/doc behavior:
  - create failing check first
  - implement minimal change
  - rerun check to PASS
- DRY + YAGNI:
  - do not duplicate existing strict gate logic in docs-only places
  - reuse existing image scripts; no new image pipeline.
- Frequent commits:
  - commit after each task above.
- No scope creep:
  - do not add quantlib
  - do not run publish/retag.

---

## Acceptance Criteria (Definition of Done)
- MA-05..MA-09 prompts exist and are executable as thread specs.
- MA-05..MA-09 results exist with required sections and evidence.
- New scripts exist and run:
  - `collect_thread_telemetry.sh`
  - `ma_dev_image_gate.sh`
- `strict_multi_agent_gate.sh` PASS.
- `ma_dev_image_gate.sh` PASS.
- Branch clean and pushed to `origin/main`.
