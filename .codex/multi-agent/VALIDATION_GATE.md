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

## Telemetry Evidence Collection (MA-05+)

Use the thread telemetry collector script to capture reproducible evidence for MA-05 and later threads:

```bash
./.codex/multi-agent/scripts/collect_thread_telemetry.sh --since 30m
```

Optional controls:
- `--until <time>` to cap the window.
- `--collector <container>` to target a non-default collector name.

Collector script behavior:
- Exits non-zero only for operational failures (for example, collector inaccessible).
- Exits zero for successful evidence extraction even when no events are present.

## Final Dev Image Acceptance Gate (MA-09)

Run the final local dev-image acceptance gate:

```bash
./.codex/multi-agent/scripts/ma_dev_image_gate.sh
```

Optional stricter mode:

```bash
./.codex/multi-agent/scripts/ma_dev_image_gate.sh --require-gcc
```

Gate required checks:
- `./.codex/scripts/strict_multi_agent_gate.sh` passes.
- `cpp26-dev-clang:dev` exists locally.
- Clang core validation passes.
- Telemetry evidence is present and stable via `collect_thread_telemetry.sh`.
