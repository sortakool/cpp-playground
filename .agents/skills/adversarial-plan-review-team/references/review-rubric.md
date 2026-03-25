# Review Rubric

Use this rubric to decide what survives into the final review.

## Severity

- `Critical`: the artifact is unsafe to execute as written; major design or
  delivery failure is likely
- `High`: substantial rework, reliability risk, or rollout risk is likely if
  unchanged
- `Medium`: the idea can still work, but a meaningful blind spot or weakness
  should be fixed first
- `Low`: useful refinement, but not a blocker

Prefer fewer high-signal findings over many low-value comments.

## Evidence Requirements

Accept a finding only if it includes:

- a clear claim
- direct evidence from the approved artifact set
- a concrete impact statement
- a concrete fix or revision direction

Reject any finding that relies on:

- vague “best practice” language with no artifact evidence
- repo files or specs outside the approved source-of-truth set
- stale assumptions from older plans, unrelated diffs, or remembered context
- reputation or style arguments with no material risk

## Finding Format

Every accepted finding must use:

`claim -> evidence -> impact -> fix`

Example:

`The CI split is incomplete -> the plan names three workflows but does not pin a runner fallback path -> benchmark execution can fail nondeterministically -> define the exact runner labels and fallback behavior`

## PASS/FAIL Criteria

Mark the artifact `PASS` only if all of these are true:

- no unresolved `Critical` or `High` findings remain
- source-of-truth ambiguity has been eliminated
- the surviving open questions are non-blocking
- the final review converges on one prioritized verdict

Mark the artifact `FAIL` if any of these are true:

- at least one `Critical` finding remains unresolved
- multiple `High` findings point to a common missing decision
- reviewers cannot agree on the source-of-truth artifact set
- the proposal cannot be executed safely without first rewriting major parts

## Duplicate And Noise Control

Merge findings when they describe the same underlying problem through different
lenses.

Discard findings that are:

- duplicate coverage from another role
- cosmetic rather than material
- unsupported by the approved artifact set
- framed too generically to be actionable

## Stale-Context Rejection Rules

Discard a finding immediately if it:

- cites a different plan, PR, or design doc than the one under review
- pulls in repo history or prior discussions not named in the source artifact
- assumes a task, command, or workflow exists without checking the current repo
- confuses speculative memory with present evidence

When discarding for stale context, name the exact mismatch in `Discarded
Findings`.
