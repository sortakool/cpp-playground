# Multi-Agent Dispatch Policy

## Decision table

| Task class | Roles | Concurrency default | Depth budget | Write ownership |
|---|---|---:|---:|---|
| Repo/config discovery | `explorer` | High (2-6) | 1 | None (read-only) |
| Docs and standards verification | `docs_researcher` | Medium (1-3) | 1 | None (read-only) |
| Risk/correctness review | `reviewer` | Medium (1-3) | 1 | None (read-only) |
| Implementation/editing | `worker` | Low (1 per domain, max 2 in parallel if write sets are disjoint) | 1 | Single-owner per file/domain |
| Polling/long waits | `monitor` | Low-Medium (1-2) | 1 | None unless explicitly required |

## Recommended defaults by task class

- Use project `agents.max_threads = 6` as the global ceiling.
- Use per-wave spawn caps from the decision table rather than always filling the global ceiling.
- Keep `agents.max_depth = 1` as default. Allow depth 2 only for bounded, explicitly justified fan-out tasks.
- For implementation waves, require disjoint file ownership before parallel writes.
- Prefer local execution for critical-path blocking tasks; delegate sidecar tasks in parallel.

## Edge-case handling

### Depth limits

- Default depth is 1 to reduce context-rot and recursive orchestration risk.
- If depth 2 is required, enforce explicit exit criteria (task count, timeout, and expected outputs) before spawning children.
- Never increase depth to compensate for unclear prompts; tighten prompt scope first.

### Stalled workers

- Treat a worker as stalled when it has no meaningful output before timeout or repeatedly asks to wait without progress.
- Route long polling to `monitor`; keep `worker` focused on concrete implementation steps.
- Retry a stalled worker once with narrowed scope, then execute locally or reassign with a tighter task boundary.

### Approval prompts from child threads

- Child agents inherit parent approval and sandbox policy by default.
- If a child requests higher approval than parent policy allows, stop escalation and return control to parent/user with the exact blocked command.
- Do not design workflows that assume child-specific approval bypass; orchestration should remain valid under inherited constraints.

## Rules

- Parallelize read-heavy tasks aggressively.
- Never run overlapping write tasks on the same file/domain.
- Prefer short summaries returned to parent thread; do not dump raw logs.
- Use `monitor` for wait loops and status polling.
- Escalate to CLI when App visibility is insufficient for active sub-agent status.
