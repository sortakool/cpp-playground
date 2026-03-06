# Multi-Agent Dispatch Policy

## Decision table

| Task class | Roles | Concurrency | Write ownership |
|---|---|---:|---|
| Repo/config discovery | `explorer` | High (2-6) | None (read-only) |
| Docs and standards verification | `docs_researcher` | Medium (1-3) | None (read-only) |
| Risk/correctness review | `reviewer` | Medium (1-3) | None (read-only) |
| Implementation/editing | `worker` | Low (1 per domain) | Single-owner per file/domain |
| Polling/long waits | `monitor` | Medium (1-3) | None unless explicitly required |

## Rules

- Parallelize read-heavy tasks aggressively.
- Never run overlapping write tasks on the same file/domain.
- Prefer short summaries returned to parent thread; do not dump raw logs.
- Use `monitor` for wait loops and status polling.
- Escalate to CLI when App visibility is insufficient for active sub-agent status.
