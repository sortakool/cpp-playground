# Hardening Checklist

Use this checklist after the immediate failure is understood.

## Minimum Bar

Choose at least one prevention artifact:

- regression test near the failing surface
- stronger validation in CI
- static analysis or type coverage
- repo automation or helper script
- AGENTS.md or process guidance
- skill update for future agents
- operational runbook or docs update

## Selection Heuristics

- If the failure was a missed edge case, prefer a test.
- If the failure was a bad default or unsafe path, prefer a guardrail in code or
  config.
- If the failure was repeated operator confusion, update AGENTS, docs, or a
  repo-local skill.
- If the failure was discoverable earlier, tighten CI or local verification.

## AGENTS And Skill Updates

Update `AGENTS.md` or a repo-local skill when the failure came from:

- stale or missing instructions
- ambiguous approval or escalation behavior
- repeated workflow-selection mistakes
- missing validation steps
- poor handoff between agents

Keep those updates concrete. Bad example: "be careful with CI".
Good example: "when a workflow touches X, run Y before dispatch".

## Close-Out Questions

Before ending the loop, answer:

1. Why did the workflow fail?
2. Why was that not prevented earlier?
3. What changed to prevent recurrence?
4. What validation proved both the fix and the prevention layer?
