# Strict Validation Gate

Run from repo root:

```bash
./.codex/scripts/strict_multi_agent_gate.sh
```

## PASS conditions

- TOML config parse succeeds for project/global config.
- `features.multi_agent = true` is effective in global + project scopes.
- Required roles exist and role config files are present.
- Publish skill remains explicit-only.
- Local collector health endpoint is reachable.
- No duplicated OTLP path errors (`/v1/logs/v1/logs`, `/v1/traces/v1/traces`) in collector forwarding error lines from the current collector runtime.
- Internal upstream forwarding is transport-stable (no retry/drop timeout errors for `otlphttp/internal_logs` or `otlphttp/internal_traces`) during the gate run.
- At least one recent Codex telemetry event appears in collector logs.

## FAIL conditions

Any failed check returns non-zero exit code and prints failing check names.
