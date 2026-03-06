# AGENTS.md

## Scope
This is the repository-level instruction file for Codex runs in this repo.

## Multi-Agent Program
- Multi-agent thread orchestration artifacts live in `.codex/multi-agent/`.
- Per-thread prompts live in `.codex/multi-agent/prompts/MA-*.md`.
- Thread outputs live in `.codex/multi-agent/results/MA-*-result.md`.

## Completion Contract (MA Threads)
- Every completed MA thread must produce a result file in `.codex/multi-agent/results/`.
- Result files must include these sections:
  - `## Findings`
  - `## Evidence Commands`
  - `## PASS/FAIL`
  - `## Blockers (Owner Thread)`
  - `## Learnings`
- After creating or updating a result file, run:
  - `./.codex/multi-agent/scripts/sync_agents_learnings.sh`

## Source of Truth
- Operational process and policy for MA threads is defined in:
  - `.codex/multi-agent/AGENTS.md`
