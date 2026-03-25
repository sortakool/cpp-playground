# MA-18 Result (Adversarial Final Acceptance)

## Findings
- claim -> "The build-optimization wave preserved the one-Dockerfile contract."  
  evidence -> `dockerfiles = ['.devcontainer/Dockerfile.host-user', 'Dockerfile']`; Dockerfile stage list remained `['base', 'clang', 'gcc', 'final', 'devcontainer']`.  
  impact -> Core repo contract remained intact; no hidden stage-graph expansion.  
  fix -> none required.

- claim -> "MA-14 implemented the authoritative smoke workflow exactly on the required runner class."  
  evidence -> workflow contains `self-hosted`, `Linux`, `X64`, `latest-kernel`; contains bake build + repo smoke script + `uv run verify run`; no hosted fallback block exists.  
  impact -> Authoritative proof path is defined correctly in CI surface.  
  fix -> none required.

- claim -> "MA-15 provided a measured benchmark surface that matches spec-required artifact fields."  
  evidence -> `benchmarks/devcontainer/schema.json` required set includes all mandated fields; scripts and pixi tasks exist for benchmark and size report.  
  impact -> Repo now has a durable, repo-owned measurement interface for optimization experiments.  
  fix -> none required.

- claim -> "MA-16 added declarative drift guards for schema/pin alignment without contract broadening."  
  evidence -> new verification suites `build-optimization.schema-surface` and `build-optimization.pin-alignment`; README only documents repo-owned commands and authoritative runner constraints.  
  impact -> Drift risk between bake defaults and Dockerfile ARG fallbacks is now bounded by verification.  
  fix -> none required.

- claim -> "The wave has authoritative runtime proof for smoke, benchmark, and optimization acceptance."  
  evidence -> MA-14/MA-15/MA-17 runtime commands all failed locally with `docker is required`; telemetry collection failed for same reason; MA-17 recorded `FAIL (blocked)`.  
  impact -> Final optimization acceptance cannot be granted on this machine; local results are structural-only.  
  fix -> rerun MA-14 smoke and MA-17 benchmark/optimization on authoritative Linux `amd64` Docker-capable runner and attach before/after artifacts.

- claim -> "MA-17 optimization experiment completed according to acceptance bar."  
  evidence -> no before/after benchmark artifacts were produced because baseline benchmark command could not execute; thread explicitly reports FAIL/blocked.  
  impact -> Optimization wave cannot pass final gate under the current evidence standard.  
  fix -> complete MA-17 on authoritative runtime surface, then re-run MA-18.

- discarded finding -> "Runner-label workflow presence alone is sufficient to mark final PASS."  
  evidence -> spec requires authoritative runtime smoke/benchmark evidence, not only structural workflow definitions.  
  impact -> Avoids false-positive acceptance from static file checks.  
  fix -> retain FAIL until runtime evidence exists.

## Evidence Commands
1. Dockerfile surface and stage-order checks:
```bash
python3 - <<'PY'
from pathlib import Path
dockerfiles = sorted(str(path) for path in Path('.').rglob('Dockerfile*') if path.is_file() and '.git/' not in str(path))
print('\n'.join(dockerfiles))
PY

python3 - <<'PY'
from pathlib import Path
text = Path('Dockerfile').read_text().splitlines()
stages = [line.split(' AS ', 1)[1].strip() for line in text if line.startswith('FROM ') and ' AS ' in line]
print(stages)
PY
```
Observed output summary: Dockerfile set and stage order match contract.

2. MA wave commit/evidence baseline:
```bash
git log --oneline -n 8
```
Observed output summary: MA-13, MA-14, MA-15, MA-16 commits are present in order.

3. Result-schema completeness checks:
```bash
python3 - <<'PY'
from pathlib import Path
required = [
 '.codex/multi-agent/results/MA-13-result.md',
 '.codex/multi-agent/results/MA-14-result.md',
 '.codex/multi-agent/results/MA-15-result.md',
 '.codex/multi-agent/results/MA-16-result.md',
 '.codex/multi-agent/results/MA-17-result.md',
]
for path in required:
    text = Path(path).read_text()
    has_sections = all(section in text for section in ('## Findings','## Evidence Commands','## PASS/FAIL','## Blockers (Owner Thread)','## Learnings'))
    print(f'{path}: sections_ok={has_sections}')
PY
```
Observed output summary: all MA-13..MA-17 result files include required sections.

4. MA-14 workflow contract checks:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('.github/workflows/devcontainer-authoritative-smoke.yml').read_text()
checks = {
  'runner_labels': all(token in text for token in ('- self-hosted','- Linux','- X64','- latest-kernel')),
  'bake_build': 'docker buildx bake -f docker-bake.hcl devcontainer --load' in text,
  'repo_smoke': './scripts/smoke-devcontainer-image.sh' in text,
  'verify_run': 'uv run verify run' in text,
}
print(checks)
PY
```
Observed output summary: all required workflow checks returned `True`.

5. Telemetry/log evidence capture attempt:
```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 120m
```
Observed output summary: command exited non-zero with `docker is required`.

6. Learnings sync:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

## PASS/FAIL
- MA-13 baseline: **PASS**
- MA-14 smoke workflow/smoke-script implementation: **PASS (structural)**
- MA-15 benchmark surface implementation: **PASS (structural)**
- MA-16 verification/docs integration: **PASS (structural)**
- MA-17 constrained optimization experiment: **FAIL (blocked, no authoritative measurement evidence)**
- Final MA-18 adversarial acceptance: **FAIL**

## Blockers (Owner Thread)
- Missing Docker-capable authoritative runtime evidence for MA-14 and MA-17 on current host.
  - Owner thread: **MA-17** (complete measured optimization experiment on authoritative Linux `amd64` surface).
- Final acceptance cannot pass while MA-17 remains blocked/fail.
  - Owner thread: **MA-18** (re-run once MA-17 evidence exists).

## Learnings
- Structural readiness (workflow/scripts/schema/docs) and authoritative runtime proof must remain explicitly separated in acceptance logic.
- Final acceptance quality improves when unsupported optimistic findings are explicitly discarded instead of softened into partial PASS language.
