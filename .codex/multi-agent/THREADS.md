# Codex App Multi-Agent Thread Split

This workspace uses an App + CLI hybrid control plane:
- Codex App: thread orchestration, review, and handoff
- Codex CLI: live sub-agent visibility, approvals, and low-level debugging

## Threads

1. `MA-00 Session Open Items`
- Fix OTEL forwarding path issues, verify collector health, verify prompt telemetry posture.
- Owner role: `worker`; monitor role: `monitor`.

2. `MA-01 Runtime Baseline`
- Validate effective global/project config precedence and role coherency.
- Roles: `explorer`, `reviewer`.

3. `MA-02 Role Topology`
- Finalize task-class dispatch policy for context-rot control.
- Roles: `docs_researcher`, `reviewer`.

4. `MA-03 Skills Trigger Matrix`
- Validate trigger intents, implicit/explicit invocation policy, and false-trigger boundaries.
- Roles: `explorer`, `reviewer`.

5. `MA-04 Strict Validation Gate`
- Run binary PASS/FAIL gate covering config, agent tools, policy, and telemetry.
- Roles: `worker`, `monitor`, `reviewer`.

## Execution order

Run `MA-00` first. Then `MA-01` and `MA-02` can run in parallel. `MA-03` follows once runtime baseline is stable. `MA-04` is final acceptance.

## Thread completion contract

Each thread must return:
- Findings summary (3-10 bullets)
- Exact evidence commands used
- PASS/FAIL for its done criteria
- Open blockers and owner thread
