# MA-16 Result (Verification + Docs Integration)

## Findings
- Added declarative verification suite `build-optimization.schema-surface` to enforce presence/shape of benchmark and smoke surfaces.
- Added declarative verification suite `build-optimization.pin-alignment` to enforce bake-variable and Dockerfile ARG fallback alignment for shared pins.
- Updated `README.md` with a tight operational section for authoritative smoke and benchmark command surfaces.
- README updates do not introduce hosted authoritative-proof claims or broaden Dockerfile/stage contracts.
- Existing contract suites were preserved; no prior verification suite was removed or weakened.
- Local `uv run verify run` execution is blocked in this environment (`uv` unavailable), so suite execution evidence is provided with direct command parity checks.
- Telemetry/log capture remains blocked locally (`docker` unavailable), recorded as structural evidence only.

## Evidence Commands
1. Canonical verify command attempt:
```bash
uv run verify run --suite build-optimization.schema-surface --suite build-optimization.pin-alignment
```
Observed output summary: command failed with `zsh:1: command not found: uv`.

2. Direct schema-surface parity check (same logic as suite):
```bash
python3 - <<'PY'
import json
from pathlib import Path
required_paths = (
    Path('benchmarks/devcontainer/schema.json'),
    Path('benchmarks/devcontainer/README.md'),
    Path('scripts/benchmark-devcontainer-build.sh'),
    Path('scripts/report-devcontainer-size.sh'),
    Path('scripts/smoke-devcontainer-image.sh'),
    Path('.github/workflows/devcontainer-authoritative-smoke.yml'),
)
missing = [str(path) for path in required_paths if not path.exists()]
if missing:
    raise SystemExit(f'missing build-optimization path(s): {missing}')
schema = json.loads(Path('benchmarks/devcontainer/schema.json').read_text())
required_fields = {
    'schema_version','run_id','git_sha','git_dirty','runner_name','runner_labels',
    'docker_version','buildx_version','scenario','platform','image_ref','timings_s',
    'image_size_bytes','compressed_size_bytes','top_layers','filesystem_sizes','result',
}
actual = set(schema.get('required', []))
if required_fields != actual:
    raise SystemExit(f'schema required mismatch: {sorted(required_fields ^ actual)}')
print('build-optimization schema surface ok')
PY
```
Observed output summary: `build-optimization schema surface ok`.

3. Direct pin-alignment parity check (same logic as suite):
```bash
python3 - <<'PY'
import re
from pathlib import Path
bake_text = Path('docker-bake.hcl').read_text()
dockerfile_text = Path('Dockerfile').read_text()
keys = ('BASE_DISTRO', 'BASE_VERSION', 'APT_SNAPSHOT', 'MISE_VERSION', 'LLVM_VERSION')
def bake_value(key: str) -> str:
    pattern = re.compile(rf'variable \"{key}\"\\s*{{\\s*default = \"([^\"]+)\"', re.MULTILINE)
    match = pattern.search(bake_text)
    if not match:
        raise SystemExit(f'missing bake variable default for {key}')
    return match.group(1)
def dockerfile_value(key: str) -> str:
    pattern = re.compile(rf'ARG {key}=([^\\n]+)')
    match = pattern.search(dockerfile_text)
    if not match:
        raise SystemExit(f'missing Dockerfile ARG default for {key}')
    return match.group(1).strip()
for key in keys:
    left = bake_value(key)
    right = dockerfile_value(key)
    if left != right:
        raise SystemExit(f'pin mismatch for {key}: bake={left!r} dockerfile={right!r}')
print('build pin alignment ok')
PY
```
Observed output summary: `build pin alignment ok`.

4. README command-surface validation:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('README.md').read_text()
for token in (
  '.github/workflows/devcontainer-authoritative-smoke.yml',
  './scripts/smoke-devcontainer-image.sh',
  './scripts/benchmark-devcontainer-build.sh --scenario cold',
  './scripts/report-devcontainer-size.sh',
  'pixi run smoke-devcontainer-image',
  'pixi run benchmark-devcontainer-build -- --scenario cold',
  'pixi run report-devcontainer-size',
  'benchmarks/devcontainer/schema.json',
):
  if token not in text:
    raise SystemExit(f'missing README token: {token}')
print('readme command-surface tokens ok')
PY
```
Observed output summary: `readme command-surface tokens ok`.

5. Telemetry/log evidence capture attempt:
```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 120m
```
Observed output summary: command exited non-zero with `docker is required`.

6. Learnings sync:
```bash
./.codex/multi-agent/scripts/sync_agents_learnings.sh
```

7. PASS commit evidence commands:
```bash
git status --short
git add verification/verification.toml README.md .codex/multi-agent/results/MA-16-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-16 verification and docs integration"
git show --name-only --oneline -n 1
```

## PASS/FAIL
- Goal 1 (verification additions for schema + pin alignment): **PASS (structural)**
- Goal 2 (README command-surface integration): **PASS**
- Goal 3 (preserve one-Dockerfile/thin-devcontainer model): **PASS**
- Goal 4 (canonical local `uv run verify run` evidence): **BLOCKED** (`uv` unavailable)
- Overall MA-16: **PASS (structural implementation complete; canonical runtime/tooling execution deferred)**

## Blockers (Owner Thread)
- Local host lacks `uv`, blocking canonical `uv run verify run` execution.
  - Owner thread: **MA-18** (final acceptance classification of structural vs authoritative evidence).
- Local host lacks Docker, blocking telemetry collector evidence.
  - Owner threads: **MA-17** (runtime benchmark proof) and **MA-18** (final acceptance).

## Learnings
- Encoding schema/pin checks in `verification.toml` provides a stable guardrail against drift without introducing a new orchestration plane.
- README updates should reference only repo-owned scripts/tasks and explicit authoritative runner constraints to avoid accidental contract expansion.
