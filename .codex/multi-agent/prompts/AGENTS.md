# AGENTS.md (Prompt Authoring)

## Scope
Applies to `.codex/multi-agent/prompts/`.

## Prompt Requirements for MA Threads
- State the thread id and objective clearly.
- Require PASS/FAIL with explicit evidence commands.
- Require blocker ownership mapping.
- Require output file path: `.codex/multi-agent/results/MA-XX-result.md`.
- Require `## Learnings` section in the result.
- Require running `./.codex/multi-agent/scripts/sync_agents_learnings.sh` after result write.

## Consistency
- Keep deliverable labels aligned with `.codex/multi-agent/AGENTS.md`.
