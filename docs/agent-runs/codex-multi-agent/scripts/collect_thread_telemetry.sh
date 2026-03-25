#!/usr/bin/env bash
set -euo pipefail

SINCE=""
UNTIL=""
COLLECTOR="codex-otel-collector"

usage() {
  cat <<USAGE
Usage: $0 --since <time> [--until <time>] [--collector <container>]

Options:
  --since <time>        Required docker logs time selector (for example: 30m or RFC3339)
  --until <time>        Optional docker logs upper-bound selector
  --collector <name>    Collector container name (default: codex-otel-collector)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)
      SINCE="${2:-}"
      shift 2
      ;;
    --until)
      UNTIL="${2:-}"
      shift 2
      ;;
    --collector)
      COLLECTOR="${2:-}"
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

if [[ -z "$SINCE" ]]; then
  echo "--since is required" >&2
  usage
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if ! docker inspect "$COLLECTOR" >/dev/null 2>&1; then
  echo "collector container not found: $COLLECTOR" >&2
  exit 1
fi

if ! docker ps --filter "name=^/${COLLECTOR}$" --format '{{.Names}}' | grep -qx "$COLLECTOR"; then
  echo "collector container not running: $COLLECTOR" >&2
  exit 1
fi

log_args=(--since "$SINCE")
if [[ -n "$UNTIL" ]]; then
  log_args+=(--until "$UNTIL")
fi

if ! RAW_LOGS="$(docker logs "${log_args[@]}" "$COLLECTOR" 2>&1)"; then
  echo "failed to read logs from collector: $COLLECTOR" >&2
  exit 1
fi

echo "== TELEMETRY WINDOW =="
printf 'collector=%s\n' "$COLLECTOR"
printf 'since=%s\n' "$SINCE"
printf 'until=%s\n' "${UNTIL:-<none>}"

printf '\n== CODEX EVENT LINES ==\n'
CODEX_EVENTS="$(printf '%s\n' "$RAW_LOGS" | rg 'event\.name=codex\.(api_request|sse_event|websocket_event|tool_result|user_prompt)' || true)"
if [[ -n "$CODEX_EVENTS" ]]; then
  printf '%s\n' "$CODEX_EVENTS"
else
  echo "(no codex event lines found in window)"
fi

printf '\n== DUPLICATED OTLP PATH ERROR SCAN ==\n'
DUP_PATH_ERRORS="$(printf '%s\n' "$RAW_LOGS" | rg 'exporterhelper/(retry_sender|queue_sender).*Post ".*/v1/(logs|traces)/v1/(logs|traces)' || true)"
if [[ -n "$DUP_PATH_ERRORS" ]]; then
  printf '%s\n' "$DUP_PATH_ERRORS"
else
  echo "(no duplicated OTLP path errors found)"
fi

printf '\n== INTERNAL RETRY/DROP TIMEOUT SCAN ==\n'
INTERNAL_RETRY_DROP="$(printf '%s\n' "$RAW_LOGS" | rg 'exporterhelper/(retry_sender|queue_sender).*(otlphttp/internal_logs|otlphttp/internal_traces).*(context deadline exceeded|i/o timeout|no more retries left|dropping data|Dropping data)' || true)"
if [[ -n "$INTERNAL_RETRY_DROP" ]]; then
  printf '%s\n' "$INTERNAL_RETRY_DROP"
else
  echo "(no retry/drop timeout signals for internal_logs/internal_traces)"
fi

exit 0
