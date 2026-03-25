---
name: adversarial-plan-review-team
description: Orchestrate a bounded multi-agent adversarial review of technical plans, pull requests, and design docs by combining skeptical plan critique, assumption busting, and evidence-first synthesis into one repeatable workflow. Use when a proposal needs disjoint lenses for implementation quality, reliability risk, and delivery impact instead of a single reviewer pass.
---

# Adversarial Plan Review Team

## Overview

Use this skill to run a compact review team for high-impact technical proposals.
It coordinates existing repo-local adversarial primitives instead of replacing
them with a generic external framework.

## Load Order

1. Load `$code-doubter` for skeptical review of the overall approach.
2. Load `$adversarial-thinking` for assumption busting, failure modes, and
   evidence checks.
3. Use `$adversarial-committee` only for short cross-examination and synthesis,
   not as the primary review engine.

Read [references/role-prompts.md](references/role-prompts.md) before assigning
roles.
Read [references/review-rubric.md](references/review-rubric.md) before
accepting, discarding, or ranking findings.

## Decision Rules

Use this skill when:

- reviewing a plan, PR, or architecture proposal that could create expensive
  downstream mistakes
- the artifact needs multiple independent lenses rather than one blended review
- you need an explicit PASS/FAIL outcome with evidence-backed revisions

Do not use this skill when:

- the task is trivial, mechanical, or already governed by a clear existing
  pattern
- the request is open-ended brainstorming without a concrete artifact
- the user actually wants a full security red-team engagement or penetration
  test

## Team Topology

Default operating mode is four active workers plus one lead and one arbiter.
Do not run all six roles as full independent crews unless the artifact is
exceptionally high stakes.

- `war-room-lead`: anchors the source-of-truth artifact, restates the goal,
  defines review scope, and assigns lenses
- `tribunal-implementation`: reviews architecture, interfaces, abstraction
  level, and maintainability
- `tribunal-reliability`: reviews correctness, security, performance, failure
  modes, and testability
- `tribunal-delivery`: reviews rollout plan, CI impact, migration risk,
  observability, and operational cost
- `adversarial-challenger`: attacks assumptions, hidden coupling, stale
  context, and unsupported claims
- `final-arbiter`: discards weak findings, merges duplicates, ranks issues, and
  produces the final verdict

## Review Workflow

1. Anchor the review on one explicit artifact only.
   Allowed examples: the current plan, the current PR diff, or one design doc.
   Stop if the source artifact is ambiguous.
2. The lead states:
   - goal of the artifact
   - scope boundaries
   - success criteria for the review
   - exact artifact set that counts as evidence
3. Run three tribunal reviews in parallel on disjoint lenses.
4. Run one adversarial challenger pass over the strongest claims and biggest
   remaining assumptions.
5. Run one short cross-examination round only for conflicting or high-severity
   findings.
6. The arbiter produces the single final review.

## Output Contract

The final review must use this exact top-level structure:

- `Goal`
- `Findings`
- `Discarded Findings`
- `Open Questions`
- `PASS/FAIL`
- `Required Revisions`

Every accepted finding must follow this format:

`claim -> evidence -> impact -> fix`

Within `Discarded Findings`, explicitly call out findings rejected for:

- wrong artifact set
- stale specs or stale repo context
- missing evidence
- duplicate coverage from another lens
- style-only objections with no material risk

## Stop Conditions

Stop and ask for clarification, or explicitly fail the review, when:

- there is no single source-of-truth artifact
- reviewers are citing different artifact sets
- a finding cannot point to evidence in the approved artifact set
- the review turns into generic debate instead of evidence-backed critique
- all surviving findings are duplicates or non-material

## Quality Bar

- Prefer materially different findings per lens over a long undifferentiated
  list.
- Prefer discarding weak findings over forcing false consensus.
- Prefer concise, direct criticism with a concrete fix.
- Keep the team evidence-first and repo-specific.
