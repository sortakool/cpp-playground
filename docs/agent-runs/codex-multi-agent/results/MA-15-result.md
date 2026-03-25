# MA-15 Result (Benchmark Surface)

## Findings
- Added benchmark runner script: `scripts/benchmark-devcontainer-build.sh`.
- Added image-size report script: `scripts/report-devcontainer-size.sh`.
- Added benchmark schema: `benchmarks/devcontainer/schema.json`.
- Added benchmark operator doc: `benchmarks/devcontainer/README.md`.
- Added `pixi` entry points for benchmark/size/smoke script surface:
  - `benchmark-devcontainer-build`
  - `report-devcontainer-size`
  - `smoke-devcontainer-image`
- Benchmark schema includes all V1-required fields from the spec:
  - run metadata, timings, image sizes, top layers, filesystem footprints, and result status.
- Scripts are shell-first and avoid introducing any new Python package/module surface.
- Local benchmark execution is blocked on this host because Docker is unavailable; implementation is structurally validated.

## Evidence Commands
1. Script syntax validation:
```bash
bash -n scripts/benchmark-devcontainer-build.sh
bash -n scripts/report-devcontainer-size.sh
```
Observed output summary: both commands exited `0`.

2. Script CLI surface validation:
```bash
./scripts/benchmark-devcontainer-build.sh --help
./scripts/report-devcontainer-size.sh --help
```
Observed output summary: expected usage and options rendered for both scripts.

3. Benchmark schema required-field validation:
```bash
python3 - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path('benchmarks/devcontainer/schema.json').read_text())
required = {
  'schema_version','run_id','git_sha','git_dirty','runner_name','runner_labels',
  'docker_version','buildx_version','scenario','platform','image_ref','timings_s',
  'image_size_bytes','compressed_size_bytes','top_layers','filesystem_sizes','result'
}
actual = set(schema.get('required', []))
if required != actual:
  raise SystemExit(f'required field mismatch: {sorted(required ^ actual)}')
print('benchmark schema required fields ok')
PY
```
Observed output summary: `benchmark schema required fields ok`.

4. Pixi task surface validation:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('pixi.toml').read_text()
for token in (
  'benchmark-devcontainer-build = "./scripts/benchmark-devcontainer-build.sh"',
  'report-devcontainer-size = "./scripts/report-devcontainer-size.sh"',
  'smoke-devcontainer-image = "./scripts/smoke-devcontainer-image.sh"',
):
  if token not in text:
    raise SystemExit(f'missing pixi task token: {token}')
print('pixi benchmark task surface tokens ok')
PY
```
Observed output summary: `pixi benchmark task surface tokens ok`.

5. Local benchmark runtime attempt:
```bash
./scripts/benchmark-devcontainer-build.sh --scenario cold
```
Observed output summary: command exited non-zero with `docker is required`.

6. Telemetry/log evidence capture attempt:
```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 120m
```
Observed output summary: command exited non-zero with `docker is required`.

7. Learnings sync:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

8. PASS commit evidence commands:
```bash
git status --short
git add scripts/benchmark-devcontainer-build.sh scripts/report-devcontainer-size.sh benchmarks/devcontainer/schema.json benchmarks/devcontainer/README.md pixi.toml .codex/multi-agent/results/MA-15-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-15 benchmark surface"
git show --name-only --oneline -n 1
```

## PASS/FAIL
- Goal 1 (schema + benchmark scripts in spec scope): **PASS (structural)**
- Goal 2 (size-report script + pixi leaf tasks): **PASS (structural)**
- Goal 3 (metadata coverage for paired-run comparison): **PASS**
- Goal 4 (local runtime benchmark execution): **BLOCKED** (`docker` unavailable on this machine)
- Overall MA-15: **PASS (structural implementation complete; authoritative runtime measurement deferred)**

## Blockers (Owner Thread)
- Local Docker-unavailable host blocks authoritative benchmark execution.
  - Owner thread: **MA-17** for before/after optimization measurement on authoritative Linux amd64 runtime.
  - Final arbitration owner: **MA-18**.

## Learnings
- Keeping benchmark tooling shell-first with JSON-schema artifacts provides reproducible measurement surfaces without adding a new control plane.
- The scenario label should remain explicit input (`cold`, `warm-repo-change`, `warm-devcontainer-change`) so paired-run comparisons stay auditable.
