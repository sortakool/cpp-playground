# AGENTS.md (Multi-Agent Program)

## Purpose
This directory defines the durable operating model for `MA-*` threads in this repository.

## Official Guidance Anchors
- Codex `AGENTS.md` behavior and precedence:
  - https://developers.openai.com/codex/guides/agents-md
- Codex MCP and OpenAI Docs MCP references:
  - https://developers.openai.com/codex/mcp/
  - https://developers.openai.com/resources/docs-mcp

## Required Thread Artifacts
- Prompt: `.codex/multi-agent/prompts/MA-XX.md`
- Result: `.codex/multi-agent/results/MA-XX-result.md`

## Result Schema (Required)
Each `MA-XX-result.md` must contain:
- `## Findings`
- `## Evidence Commands`
- `## PASS/FAIL`
- `## Blockers (Owner Thread)`
- `## Learnings`

## Learnings Auto-Sync (Required)
After each result file update, run:
- `./.codex/multi-agent/scripts/sync_agents_learnings.sh`

## Thread Validation And Commit (Required)
For `MA-01` and all later threads:
- Run thread-specific validation commands before declaring PASS.
- If thread status is PASS, stage and commit thread changes in the same thread.
- Include commit evidence in the result under `## Evidence Commands` (at minimum: `git status --short`, `git add ...`, `git commit ...`, `git show --name-only --oneline -n 1`).
- If validation fails, do not commit incomplete thread state; report blockers and owner thread.

The script regenerates the learnings section below from all `MA-*-result.md` files.
Do not manually edit inside the managed block.

## Learnings Index (Auto-Generated)
<!-- BEGIN AUTO-LEARNINGS -->
- [MA-00] Validate transport stability, not just config shape and health endpoint status, before marking telemetry threads as PASS.
- [MA-00] Scope duplicate-path checks to collector exporter transport error lines to avoid false positives from command text in telemetry payloads.
- [MA-00] Keep strict-gate checks aligned with documented PASS criteria to prevent result drift.
- [MA-01] For MA runtime baselines, include a computed effective-settings matrix (global vs project) rather than only listing raw TOML content.
- [MA-01] Role coherence checks are stronger when validated both structurally (declared + file exists) and behaviorally (sandbox alignment by role intent).
- [MA-01] Approval/safety checks should explicitly separate runtime-level controls from skill-level invocation policies to avoid false conflict reports.
- [MA-02] Multi-agent policy should encode depth and wait behavior explicitly; leaving these implicit increases orchestration drift under load.
- [MA-02] Child-thread approvals must be treated as inherited constraints, not independently escalatable capabilities.
- [MA-02] Concurrency defaults are safer as per-task-class wave caps under a global ceiling than as a single flat thread count.
<!-- END AUTO-LEARNINGS -->
