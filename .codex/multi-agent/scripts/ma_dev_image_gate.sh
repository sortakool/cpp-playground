#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REQUIRE_GCC=0
SINCE_WINDOW="120m"

usage() {
  cat <<USAGE
Usage: $0 [--require-gcc] [--since <time>]

Options:
  --require-gcc   Require gcc core validation as a hard check.
  --since <time>  Telemetry window for collector check (default: 120m).
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-gcc)
      REQUIRE_GCC=1
      shift
      ;;
    --since)
      SINCE_WINDOW="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

failures=()

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures+=("$1"); }

run_check() {
  local label="$1"
  shift
  if "$@"; then
    pass "$label"
  else
    fail "$label"
  fi
}

run_check "strict multi-agent gate" \
  bash -lc "cd '$ROOT_DIR' && ./.codex/scripts/strict_multi_agent_gate.sh >/tmp/ma-dev-gate-strict.log 2>&1"

run_check "clang core image exists locally (cpp26-dev-clang:dev)" \
  bash -lc "docker image inspect cpp26-dev-clang:dev >/dev/null 2>&1"

run_check "clang core validation" \
  bash -lc "cd '$ROOT_DIR' && ./.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain clang --flavor core --image-tag dev >/tmp/ma-dev-gate-clang.log 2>&1"

TELEMETRY_CAPTURE=""
if TELEMETRY_CAPTURE="$(bash -lc "cd '$ROOT_DIR' && ./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since '$SINCE_WINDOW'" 2>&1)"; then
  if grep -q "(no codex event lines found in window)" <<<"$TELEMETRY_CAPTURE"; then
    fail "telemetry evidence present and stable"
  elif grep -q "== DUPLICATED OTLP PATH ERROR SCAN ==" <<<"$TELEMETRY_CAPTURE" && ! grep -q "(no duplicated OTLP path errors found)" <<<"$TELEMETRY_CAPTURE"; then
    fail "telemetry evidence present and stable"
  elif grep -q "== INTERNAL RETRY/DROP TIMEOUT SCAN ==" <<<"$TELEMETRY_CAPTURE" && ! grep -q "(no retry/drop timeout signals for internal_logs/internal_traces)" <<<"$TELEMETRY_CAPTURE"; then
    fail "telemetry evidence present and stable"
  else
    pass "telemetry evidence present and stable"
  fi
else
  fail "telemetry evidence present and stable"
fi

if [[ "$REQUIRE_GCC" -eq 1 ]]; then
  run_check "gcc core validation (required)" \
    bash -lc "cd '$ROOT_DIR' && ./.agents/skills/cpp26-dev-image-validate/scripts/test_images.sh --toolchain gcc --flavor core --image-tag dev >/tmp/ma-dev-gate-gcc.log 2>&1"
else
  pass "gcc core validation optional skip (--require-gcc not set)"
fi

if ((${#failures[@]} > 0)); then
  echo "DEV IMAGE GATE RESULT: FAIL"
  exit 1
fi

echo "DEV IMAGE GATE RESULT: PASS"
exit 0
