# MA-17 Result (Constrained Optimization Experiment)

## Findings
- Selected optimization family for MA-17 was build-context hygiene (`.dockerignore`) because it is explicitly allowed in V1 scope.
- MA-17 requires before/after evidence using the repo-owned benchmark surface before landing any optimization change.
- Baseline benchmark execution could not start on this machine because Docker is unavailable.
- Size-report execution also failed for the same reason (`docker is required`).
- Because measurement prerequisites are missing, no optimization patch was applied; forcing an unmeasured change would violate MA-17 constraints.
- MA-17 is intentionally reported as blocked/fail rather than passing with unverified assumptions.

## Evidence Commands
1. Required baseline benchmark attempt:
```bash
./scripts/benchmark-devcontainer-build.sh --scenario cold --output /tmp/ma17-before.json
```
Observed output summary: command exited non-zero with `docker is required`.

2. Required size-report attempt:
```bash
./scripts/report-devcontainer-size.sh --image-ref ghcr.io/ray-manaloto/cpp-devcontainer:dev
```
Observed output summary: command exited non-zero with `docker is required`.

3. Telemetry/log evidence capture attempt:
```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 120m
```
Observed output summary: command exited non-zero with `docker is required`.

4. Learnings sync:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

## PASS/FAIL
- Goal 1 (implement one allowed optimization hypothesis): **FAIL (blocked by missing runtime proof surface)**
- Goal 2 (collect before/after measurement evidence): **FAIL**
- Goal 3 (keep Dockerfile/stage/devcontainer contract intact): **PASS** (no contract changes applied)
- Goal 4 (reject weak/noisy evidence rather than force merge): **PASS**
- Overall MA-17: **FAIL (blocked)**

## Blockers (Owner Thread)
- Docker unavailable on current host prevents benchmark and size evidence generation.
  - Owner thread: **MA-18** for final acceptance classification and follow-up gating.
  - External prerequisite: run MA-17 benchmark/optimization on authoritative Linux `amd64` Docker-capable runner.

## Learnings
- MA-17 should hard-fail when benchmark prerequisites are absent; no optimization patch should land without before/after evidence.
- Structural script/workflow readiness is not a substitute for authoritative runtime measurement in optimization acceptance.
