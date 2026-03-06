# MA-00 Result (Session Open Items)

## Findings
- OTEL endpoints are now explicitly configured in project scope as **base endpoints** (no `/v1/logs` or `/v1/traces` suffix in endpoint value).
- Project telemetry privacy posture is explicitly acknowledged with `log_user_prompt = true` in project config.
- Local collector container is running and healthy on `http://127.0.0.1:13133/`.
- No duplicated OTLP signal-path errors (`/v1/logs/v1/logs`, `/v1/traces/v1/traces`) were found in recent collector transport errors.
- Recent Codex telemetry events are present in collector logs.

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
  rg 'Post ".*/v1/logs/v1/logs|Post ".*/v1/traces/v1/traces'
```

4. Verify recent Codex telemetry events are present:
```bash
docker logs --since 30m codex-otel-collector 2>&1 | \
  rg 'event\.name=codex\.(api_request|sse_event|websocket_event|tool_result|user_prompt)' | tail -n 5
```

## PASS/FAIL
- Goal 1 (base endpoints): **PASS**
- Goal 2 (collector health): **PASS**
- Goal 3 (`log_user_prompt=true` acknowledged): **PASS**
- Overall MA-00: **PASS**

## Blockers (Owner Thread)
- None.
