# MA-00 Result (Session Open Items)

## Findings
- OTEL endpoints are now explicitly configured in project scope as **base endpoints** (no `/v1/logs` or `/v1/traces` suffix in endpoint value).
- Project telemetry privacy posture is explicitly acknowledged with `log_user_prompt = true` in project config.
- Local collector container is running and healthy on `http://127.0.0.1:13133/`.
- No duplicated OTLP signal-path errors (`/v1/logs/v1/logs`, `/v1/traces/v1/traces`) were found in collector forwarding transport error lines.
- Recent Codex telemetry events are present in collector logs.
- Internal upstream forwarding currently shows repeated timeout retries and dropped telemetry batches (`otlphttp/internal_logs`, `otlphttp/internal_traces`).

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

4. Verify internal forwarding stability (retries/drops):
```bash
docker logs --since 10m codex-otel-collector 2>&1 | \
  rg 'exporterhelper/(retry_sender|queue_sender).*(otlphttp/internal_logs|otlphttp/internal_traces).*(context deadline exceeded|i/o timeout|no more retries left|Dropping data)'
```

5. Verify recent Codex telemetry events are present:
```bash
docker logs --since 30m codex-otel-collector 2>&1 | \
  rg 'event\.name=codex\.(api_request|sse_event|websocket_event|tool_result|user_prompt)' | tail -n 5
```

## PASS/FAIL
- Goal 1 (base endpoints): **PASS**
- Goal 2 (collector health): **PASS**
- Goal 3 (`log_user_prompt=true` acknowledged): **PASS**
- Internal upstream forwarding stability: **FAIL** (timeouts/retries/drops present)
- Overall MA-00: **FAIL**

## Blockers (Owner Thread)
- Internal upstream endpoint `http://44.220.132.99:4318` is intermittently unavailable from this host, causing exporter retries and drops.
- Owner thread: `MA-00` (stabilize internal collector reachability before declaring telemetry closure).

## Learnings
- Validate transport stability, not just config shape and health endpoint status, before marking telemetry threads as PASS.
- Scope duplicate-path checks to collector exporter transport error lines to avoid false positives from command text in telemetry payloads.
- Keep strict-gate checks aligned with documented PASS criteria to prevent result drift.
