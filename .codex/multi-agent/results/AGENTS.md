# AGENTS.md (Result Files)

## Scope
Applies to `.codex/multi-agent/results/`.

## Result File Requirements
Each `MA-XX-result.md` must include:
- `## Findings`
- `## Evidence Commands`
- `## PASS/FAIL`
- `## Blockers (Owner Thread)`
- `## Learnings`

For `MA-01` and later threads, `## Evidence Commands` must include commit evidence:
- `git status --short`
- `git add ...`
- `git commit ...`
- `git show --name-only --oneline -n 1`

## Learnings Format
Use concise bullets that are reusable as future operating guidance.

## Post-Write Action
After any update to a result file, run:
- `./.codex/multi-agent/scripts/sync_agents_learnings.sh`
