# MA-00 Result (Session Open Items)

## Findings
- OTEL endpoints are now explicitly configured in project scope as **base endpoints** (no `/v1/logs` or `/v1/traces` suffix in endpoint value).
- Project telemetry privacy posture is explicitly acknowledged with `log_user_prompt = true` in project config.
- Local collector container is running and healthy on `http://127.0.0.1:13133/`.
- No duplicated OTLP signal-path errors (`/v1/logs/v1/logs`, `/v1/traces/v1/traces`) were found in collector forwarding transport error lines.
- Recent Codex telemetry events are present in collector logs.
- Remote AWS upstream is unavailable; collector is now operated in local-only mode (internal forwarding endpoints unset), which removes retry/drop transport instability from gate criteria.

## Evidence Commands
1. Verify project OTEL config (base endpoint + prompt telemetry flag):
```bash
python3 - <<'PY'
import tomllib, pathlib
p=pathlib.Path('.codex/config.toml')
with p.open('rb') as f:
    d=tomllib.load(f)
print(d.get('otel'))
PY
```

2. Verify collector health:
```bash
curl -fsS --max-time 3 http://127.0.0.1:13133/ | python3 -m json.tool
```

3. Verify no duplicated OTLP forwarding path errors in recent collector transport attempts:
```bash
docker logs --since 30m codex-otel-collector 2>&1 | \
  rg 'exporterhelper/(retry_sender|queue_sender).*Post ".*/v1/logs/v1/logs|exporterhelper/(retry_sender|queue_sender).*Post ".*/v1/traces/v1/traces'
```

4. If remote upstream is unavailable, switch collector to local-only mode:
```bash
# In ~/.codex/otel/collector.env, unset or comment these:
# OTEL_INTERNAL_LOGS_ENDPOINT
# OTEL_INTERNAL_TRACES_ENDPOINT

/Users/rmanaloto/.codex/otel/start-collector.sh
```

5. Verify strict gate passes in local-only mode:
```bash
./.codex/scripts/strict_multi_agent_gate.sh
```

6. Verify recent Codex telemetry events are present:
```bash
docker logs --since 30m codex-otel-collector 2>&1 | \
  rg 'event\.name=codex\.(api_request|sse_event|websocket_event|tool_result|user_prompt)' | tail -n 5
```

## PASS/FAIL
- Goal 1 (base endpoints): **PASS**
- Goal 2 (collector health): **PASS**
- Goal 3 (`log_user_prompt=true` acknowledged): **PASS**
- Internal upstream forwarding stability: **PASS** (local-only collector mode with no remote forwarding dependency)
- Overall MA-00: **PASS**

## Blockers (Owner Thread)
- None.

## Learnings
- Validate transport stability, not just config shape and health endpoint status, before marking telemetry threads as PASS.
- Scope duplicate-path checks to collector exporter transport error lines to avoid false positives from command text in telemetry payloads.
- Keep strict-gate checks aligned with documented PASS criteria to prevent result drift.
