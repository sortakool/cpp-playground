# MA-13 Result (Build Optimization Baseline)

## Findings
- Invariant map (must not be violated by MA-14..MA-18):
  - Preserve one root `Dockerfile` + one thin `.devcontainer/Dockerfile.host-user` overlay.
  - Preserve stage order and names exactly: `base`, `clang`, `gcc`, `final`, `devcontainer`.
  - Preserve `devcontainer` deriving from `final`; no new Dockerfile topology or control plane.
  - Keep Linux `amd64` as authoritative proof surface (`docker-bake.hcl` and `.devcontainer/devcontainer.json` both encode `linux/amd64`).
  - Preserve SSH runtime contract path `/tmp/cpp-playground-ssh-agent.sock` and initialize path `.devcontainer/initialize-host.sh`.
  - Keep broad verification gate split: fast hosted `repo-verify` and authoritative self-hosted `latest-kernel` runner class.
- MA-14 write scope is fixed to:
  - `.github/workflows/devcontainer-authoritative-smoke.yml`
  - `scripts/smoke-devcontainer-image.sh`
- MA-15 write scope is fixed to:
  - `scripts/benchmark-devcontainer-build.sh`
  - `scripts/report-devcontainer-size.sh`
  - `benchmarks/devcontainer/schema.json`
  - `benchmarks/devcontainer/README.md`
  - `pixi.toml`
- MA-16 write scope is fixed to:
  - `verification/verification.toml`
  - `README.md`
- Integration dependency order for the build-optimization wave:
  - MA-13 baseline and scope lock.
  - MA-14, MA-15, MA-16 in parallel (strictly disjoint scopes).
  - Integrate and validate MA-14..MA-16 outputs together.
  - MA-17 optimization experiment only after benchmark/smoke/verification/docs surfaces exist.
  - MA-18 adversarial acceptance last, with claim->evidence->impact->fix checks.
- Missing surfaces that downstream threads must add:
  - Authoritative smoke workflow file (`devcontainer-authoritative-smoke`).
  - Repo-owned devcontainer smoke script.
  - Benchmark schema and benchmark/size scripts.
  - Pixi task entry points for new smoke/benchmark surface.
  - Verification checks for benchmark schema and bake/Dockerfile pin-alignment assumptions.
  - README operational command-surface updates for the new scripts/workflow.
- Telemetry/log evidence collection was attempted but this environment cannot run Docker telemetry collectors; that is recorded as structural evidence, not runtime proof.
- Thread-specific validation checklist for downstream execution:
  - MA-14: validate workflow targets `self-hosted`,`Linux`,`X64`,`latest-kernel`; validate script is repo-owned and executable; no hosted fallback; validate structural YAML syntax and script shellcheck where available.
  - MA-15: validate schema shape against required fields; validate benchmark script records metadata and scenario labels; validate pixi task wiring resolves commands.
  - MA-16: validate verification suites still pass contract checks; validate README reflects only supported workflows and authoritative Linux `amd64` guidance.
  - MA-17: run before/after measurements with repo-owned scripts; reject optimization if evidence is noisy or trade-off fails thresholds.
  - MA-18: adversarially challenge every completion claim against spec contracts and command evidence; mark structural-only validation distinctly from authoritative runtime proof.

## Evidence Commands
1. Stage-contract validation:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('Dockerfile').read_text().splitlines()
stages = [line.split(' AS ', 1)[1].strip() for line in text if line.startswith('FROM ') and ' AS ' in line]
expected = ['base', 'clang', 'gcc', 'final', 'devcontainer']
if stages != expected:
    raise SystemExit(f'unexpected stage order: {stages}')
print('stage order ok')
PY
```
Observed output summary: `stage order ok`.

2. Bake-surface token validation:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('docker-bake.hcl').read_text()
required = (
  'variable "PLATFORM"',
  'default = "linux/amd64"',
  'target "base"',
  'target "clang"',
  'target "gcc"',
  'target "final"',
  'target "devcontainer"',
  'group "default"',
)
for token in required:
  if token not in text:
    raise SystemExit(f'missing token: {token}')
print('bake surface contract tokens ok')
PY
```
Observed output summary: `bake surface contract tokens ok`.

3. Devcontainer runtime-contract validation:
```bash
python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('.devcontainer/devcontainer.json').read_text())
assert '--platform=linux/amd64' in cfg.get('runArgs', []), 'missing linux/amd64 runArg'
assert cfg.get('remoteEnv', {}).get('SSH_AUTH_SOCK') == '/tmp/cpp-playground-ssh-agent.sock', 'unexpected SSH_AUTH_SOCK'
assert cfg.get('initializeCommand') == '${localWorkspaceFolder}/.devcontainer/initialize-host.sh', 'unexpected initializeCommand'
print('devcontainer runtime contract tokens ok')
PY
```
Observed output summary: `devcontainer runtime contract tokens ok`.

4. Source-of-truth file presence validation:
```bash
python3 - <<'PY'
from pathlib import Path
required = [
 'spec/2026-03-23-devcontainer-build-optimization-spec.md',
 '.codex/multi-agent/THREADS.md',
 '.codex/multi-agent/prompts/MA-13.md',
 '.codex/multi-agent/prompts/MA-14.md',
 '.codex/multi-agent/prompts/MA-15.md',
 '.codex/multi-agent/prompts/MA-16.md',
 '.codex/multi-agent/prompts/MA-17.md',
 '.codex/multi-agent/prompts/MA-18.md',
]
missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit(f'missing required source files: {missing}')
print('ma13 source-of-truth files present')
PY
```
Observed output summary: `ma13 source-of-truth files present`.

5. Telemetry/log evidence capture attempt:
```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 120m
```
Observed output summary: command exited non-zero with `docker is required` on this machine, so telemetry evidence is structurally blocked in the current execution environment.

6. Learnings sync:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

7. PASS commit evidence commands:
```bash
git status --short
git add .codex/multi-agent/results/MA-13-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-13 build optimization baseline"
git show --name-only --oneline -n 1
```

## PASS/FAIL
- Goal 1 (map hard invariants from spec + current repo surface): **PASS**
- Goal 2 (define exact MA-14/15/16 write-scope split): **PASS**
- Goal 3 (identify missing workflow/script/verification/doc surfaces): **PASS**
- Goal 4 (dependency order + thread validation checklist for MA-14..MA-18): **PASS**
- Telemetry/runtime proof status on this machine: **STRUCTURALLY BLOCKED** (`docker` unavailable).
- Overall MA-13: **PASS (structural baseline complete; authoritative runtime evidence deferred to owner threads on Linux amd64-capable surface)**.

## Blockers (Owner Thread)
- `docker` unavailable in current execution environment, blocking local telemetry collector evidence capture.
  - Owner thread: **MA-14** (authoritative smoke workflow proves on self-hosted Linux `amd64`).
- Authoritative benchmark/runtime proof cannot be established on this machine.
  - Owner thread: **MA-17** (before/after optimization evidence on authoritative surface).
- Final acceptance must treat missing runtime authority as blocked rather than implied.
  - Owner thread: **MA-18**.

## Learnings
- Locking disjoint write scopes at MA-13 materially reduces merge/conflict risk for MA-14/15/16 parallel execution.
- For this wave, telemetry and runtime evidence must be explicitly labeled structural vs authoritative; missing Docker/amd64 runtime capability is a blocker, not a hidden PASS.
