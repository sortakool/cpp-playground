#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_CFG="$ROOT_DIR/.codex/config.toml"
GLOBAL_CFG="$HOME/.codex/config.toml"
PUBLISH_POLICY="$ROOT_DIR/.agents/skills/cpp26-dev-image-publish/agents/openai.yaml"
COLLECTOR_NAME="${OTEL_COLLECTOR_CONTAINER_NAME:-codex-otel-collector}"

failures=()
pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures+=("$1"); }

check_file() {
  local p="$1"
  local l="$2"
  if [[ -f "$p" ]]; then
    pass "$l"
  else
    fail "$l ($p missing)"
  fi
}

check_file "$PROJECT_CFG" "project config exists"
check_file "$GLOBAL_CFG" "global config exists"
check_file "$PUBLISH_POLICY" "publish policy file exists"

python3 - <<'PY' "$PROJECT_CFG" "$GLOBAL_CFG" || exit 1
import pathlib, sys, tomllib
pc = pathlib.Path(sys.argv[1])
gc = pathlib.Path(sys.argv[2])
for p in (pc, gc):
    with p.open('rb') as f:
        tomllib.load(f)
print('PASS: toml parse ok (project/global)')
PY

python3 - <<'PY' "$PROJECT_CFG" "$GLOBAL_CFG" || fail "multi_agent feature flag enabled in both scopes"
import pathlib, sys, tomllib
pc = pathlib.Path(sys.argv[1])
gc = pathlib.Path(sys.argv[2])
with pc.open('rb') as f:
    p = tomllib.load(f)
with gc.open('rb') as f:
    g = tomllib.load(f)
ok = p.get('features', {}).get('multi_agent') is True and g.get('features', {}).get('multi_agent') is True
print('PASS: multi_agent enabled in project+global' if ok else 'FAIL: multi_agent not enabled in both scopes')
raise SystemExit(0 if ok else 1)
PY

for role in explorer docs_researcher worker reviewer monitor; do
  if rg -n "^\[agents\.${role}\]" "$PROJECT_CFG" >/dev/null; then
    pass "role declared: $role"
  else
    fail "role declared: $role"
  fi
  if [[ -f "$ROOT_DIR/.codex/agents/${role}.toml" ]]; then
    pass "role config exists: $role"
  else
    fail "role config exists: $role"
  fi
done

if rg -n '^policy:' "$PUBLISH_POLICY" >/dev/null && rg -n 'allow_implicit_invocation:\s*false' "$PUBLISH_POLICY" >/dev/null; then
  pass "publish skill explicit-only policy"
else
  fail "publish skill explicit-only policy"
fi

collector_up=0
for _ in {1..5}; do
  if docker ps --filter "name=^/${COLLECTOR_NAME}$" --format '{{.Names}}' | grep -qx "$COLLECTOR_NAME"; then
    collector_up=1
    break
  fi
  sleep 1
done
if [[ "$collector_up" -eq 1 ]]; then
  pass "collector container running"
else
  fail "collector container running"
fi

collector_healthy=0
for _ in {1..8}; do
  if curl --max-time 2 -fsS http://127.0.0.1:13133/ >/dev/null; then
    collector_healthy=1
    break
  fi
  sleep 1
done
if [[ "$collector_healthy" -eq 1 ]]; then
  pass "collector health endpoint reachable"
else
  fail "collector health endpoint reachable"
fi

collector_started_at="$(docker inspect --format '{{.State.StartedAt}}' "$COLLECTOR_NAME" 2>/dev/null || true)"
if [[ -n "$collector_started_at" ]]; then
  RECENT_LOGS="$(docker logs --since "$collector_started_at" "$COLLECTOR_NAME" 2>&1 || true)"
else
  RECENT_LOGS="$(docker logs --since 20m "$COLLECTOR_NAME" 2>&1 || true)"
fi
FORWARDING_LOGS="$(grep -E 'exporterhelper/(retry_sender|queue_sender)' <<<"$RECENT_LOGS" || true)"

if grep -Eq 'exporterhelper/(retry_sender|queue_sender).*Post ".*\/v1\/logs\/v1\/logs' <<<"$FORWARDING_LOGS"; then
  fail "no duplicated logs path in collector outbound requests"
else
  pass "no duplicated logs path in collector outbound requests"
fi

if grep -Eq 'exporterhelper/(retry_sender|queue_sender).*Post ".*\/v1\/traces\/v1\/traces' <<<"$FORWARDING_LOGS"; then
  fail "no duplicated traces path in collector outbound requests"
else
  pass "no duplicated traces path in collector outbound requests"
fi

if grep -Eq 'exporterhelper/(retry_sender|queue_sender).*(otlphttp/internal_logs|otlphttp/internal_traces).*(context deadline exceeded|i/o timeout|no more retries left|dropping data|Dropping data)' <<<"$FORWARDING_LOGS"; then
  fail "internal upstream forwarding transport is stable (no retries/drops)"
else
  pass "internal upstream forwarding transport is stable (no retries/drops)"
fi

if grep -Eq 'event\.name=codex\.(api_request|sse_event|websocket_event|tool_result|user_prompt)' <<<"$RECENT_LOGS"; then
  pass "recent codex telemetry events observed"
else
  fail "recent codex telemetry events observed"
fi

if ((${#failures[@]} > 0)); then
  echo
  echo "STRICT GATE RESULT: FAIL"
  printf 'Failed checks:\n'
  for item in "${failures[@]}"; do
    printf ' - %s\n' "$item"
  done
  exit 1
fi

echo
echo "STRICT GATE RESULT: PASS"
