# MA-14 Result (Authoritative Smoke Gate)

## Findings
- Implemented authoritative smoke workflow at `.github/workflows/devcontainer-authoritative-smoke.yml`.
- Workflow is constrained to required runner labels only: `self-hosted`, `Linux`, `X64`, `latest-kernel`.
- Workflow executes the required sequence with repo-owned commands:
  - `docker buildx bake -f docker-bake.hcl devcontainer --load`
  - `./scripts/smoke-devcontainer-image.sh`
  - `uv run verify run`
- Implemented repo-owned smoke script at `scripts/smoke-devcontainer-image.sh`.
- Smoke script validates image presence, runtime package/tool commands, and both reflection compiler lanes (`clang-p2996`, `gcc-reflection`) inside the built image.
- No hosted fallback was introduced; authoritative proof remains bound to the self-hosted Linux `amd64` lane.
- Local authoritative runtime execution is blocked in this environment (`docker` unavailable), so this thread is structurally validated but not locally authoritative.

## Evidence Commands
1. Script syntax validation:
```bash
bash -n scripts/smoke-devcontainer-image.sh
```
Observed output summary: exit code `0`.

2. Script CLI surface validation:
```bash
./scripts/smoke-devcontainer-image.sh --help
```
Observed output summary: usage/options rendered as expected.

3. Workflow contract token validation:
```bash
python3 - <<'PY'
from pathlib import Path
text = Path('.github/workflows/devcontainer-authoritative-smoke.yml').read_text()
required = [
  'name: devcontainer-authoritative-smoke',
  'runs-on:',
  '- self-hosted',
  '- Linux',
  '- X64',
  '- latest-kernel',
  'docker buildx bake -f docker-bake.hcl devcontainer --load',
  './scripts/smoke-devcontainer-image.sh',
  'uv run verify run',
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit(f'missing workflow token(s): {missing}')
print('workflow contract tokens ok')
PY
```
Observed output summary: `workflow contract tokens ok`.

4. Local runtime smoke attempt (authoritative proof blocked here):
```bash
./scripts/smoke-devcontainer-image.sh
```
Observed output summary: command exited non-zero with `docker is required`.

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
git add .github/workflows/devcontainer-authoritative-smoke.yml scripts/smoke-devcontainer-image.sh .codex/multi-agent/results/MA-14-result.md .codex/multi-agent/AGENTS.md
git commit -m "ma: complete MA-14 authoritative smoke gate"
git show --name-only --oneline -n 1
```

## PASS/FAIL
- Goal 1 (authoritative workflow implementation): **PASS (structural)**
- Goal 2 (repo-owned smoke script implementation): **PASS (structural)**
- Goal 3 (self-hosted latest-kernel alignment, no hosted fallback): **PASS**
- Goal 4 (local authoritative runtime proof): **BLOCKED** (`docker` unavailable on this machine)
- Overall MA-14: **PASS (structural implementation complete; authoritative runtime proof deferred to self-hosted Linux amd64 runner)**

## Blockers (Owner Thread)
- Local environment cannot execute Docker-backed authoritative smoke (`docker is required`).
  - Owner thread: **MA-17** for measurement/proof on authoritative runtime surface.
  - Final arbitration owner: **MA-18** to classify this as structural-only evidence on local host.

## Learnings
- A dedicated repo-owned smoke script keeps workflow logic minimal and auditable while preserving the authoritative self-hosted proof contract.
- On non-Docker-capable local sessions, MA threads must explicitly mark runtime checks as blocked/structural rather than claiming authoritative PASS.
