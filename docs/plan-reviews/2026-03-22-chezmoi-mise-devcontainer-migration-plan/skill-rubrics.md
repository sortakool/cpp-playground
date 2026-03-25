## adversarial-thinking
- Local file: `.agents/skills/adversarial-thinking/SKILL.md`
- Upstream repo: `wojons/skills`
- Intended use in this gate: main structured adversarial lens

## When to use me

Use this skill when:
- Making high-stakes decisions with significant consequences
- Designing systems that must withstand real-world challenges
- Preparing for security reviews, audits, or compliance checks
- Building resilience against failures, attacks, or market changes
- Preventing groupthink and confirmation bias in teams
- Stress-testing ideas, designs, or implementations
- Improving system security and robustness
- Developing critical thinking skills across the organization
- Preparing for competitive environments or adversarial conditions

## Adversarial Thinking Framework

Adversarial thinking applies multiple complementary perspectives to systematically challenge and improve ideas:

### 1. **Devil's Advocate** (@skills/devils-advocate)
- **Purpose**: Challenge ideas through logical counterarguments and alternative perspectives
- **Focus**: Logical reasoning, argument quality, alternative explanations
- **When to use**: Decision-making, proposal evaluation, preventing groupthink
- **Output**: Counterarguments, weaknesses, alternative approaches

### 2. **Assumption Buster** (@skills/assumption-buster)
- **Purpose**: Aggressively identify and disprove assumptions through counterexamples
- **Focus**: Finding where assumptions fail, edge cases, failure modes
- **When to use**: Critical systems, high-failure-cost scenarios, risk assessment
- **Output**: Busted assumptions, failure scenarios, risk areas

### 3. **Red Team** (@skills/redteam)
- **Purpose**: Think like an attacker to identify security vulnerabilities
- **Focus**: Security weaknesses, penetration vectors, attack paths
- **When to use**: Security assessments, penetration testing, defense preparation
- **Output**: Vulnerabilities, attack simulations, security recommendations

### 4. **White Hat** (@skills/white-hat)
- **Purpose**: Build defensive security capabilities and implement security by design
- **Focus**: Protective controls, security architecture, ethical testing
- **When to use**: Security implementation, compliance, defense building
- **Output**: Security controls, defense recommendations, security posture

### 5. **Trust But Verify** (@skills/trust-but-verify)
- **Purpose**: Independently verify claims rather than trusting assumptions
- **Focus**: Evidence validation, claim verification, reality checking
- **When to use**: Validating test results, progress claims, system capabilities
- **Output**: Verification results, discrepancies, confidence assessments

## When to Use Which Adversarial Perspective

### For Technical Decisions:
- **Architecture choices**: Devil's Advocate + Assumption Buster
- **Technology selection**: Devil's Advocate + Trust But Verify
- **Implementation details**: Assumption Buster + White Hat
- **Security design**: Red Team + White Hat

### For Product Decisions:
- **Feature prioritization**: Devil's Advocate + Assumption Buster
- **User experience**: Assumption Buster + Trust But Verify
- **Market strategy**: Devil's Advocate + Red Team (competitive analysis)
- **Business model**: Assumption Buster + Trust But Verify

### For Security Assessments:
- **Penetration testing**: Red Team primary, White Hat secondary
- **Security architecture**: White Hat primary, Red Team secondary
- **Incident response**: White Hat primary, Trust But Verify secondary
- **Compliance**: White Hat primary, Devil's Advocate secondary

### For Risk Management:
- **Risk identification**: Assumption Buster primary
- **Risk assessment**: Trust But Verify primary
- **Risk mitigation**: White Hat primary
- **Risk monitoring**: Trust But Verify primary

## code-doubter
- Local file: `.agents/skills/code-doubter/SKILL.md`
- Upstream repo: `reminiscent-io/wanderluxe`
- Intended use in this gate: anti-overengineering and simplification lens

## How to Review a Plan

When you receive a plan to review, work through these lenses in order. Not
every lens will surface issues — that's fine. Call out what's strong just as
clearly as what needs work.

### 1. Understand the Intent

Before critiquing anything, make sure you understand what the plan is actually
trying to accomplish. Restate the goal in one sentence. If the goal itself
seems off (solving the wrong problem, addressing a symptom rather than a root
cause), flag that first — no point optimizing a plan that's pointed in the
wrong direction.

### 2. Challenge the Approach

Ask yourself: is there a fundamentally simpler way to achieve this goal?
Engineers tend to reach for familiar patterns even when a simpler one exists.
Common things to watch for:

- **Over-abstraction**: Building generic systems when a specific solution
  would be clearer and faster. "You Aren't Gonna Need It" is usually right.
- **Wrong level of complexity**: Using a state management library when React
  state would suffice. Adding a database when a file would do. Reaching for
  microservices when a monolith is fine.
- **Reinventing existing solutions**: Is there a well-maintained library or
  platform feature that already does this? A built-in browser API? A framework
  convention?
- **Premature optimization**: Solving performance problems that don't exist
  yet, at the cost of simplicity.
- **Missing the obvious**: Sometimes the simplest approach is just... not
  doing the thing at all, or solving it with a configuration change rather
  than code.

### 3. Evaluate the Architecture

Look at how the pieces fit together:

- **Separation of concerns**: Are responsibilities cleanly divided, or is
  business logic leaking into UI components (or vice versa)?
- **Data flow**: Is data flowing in a way that's easy to trace and debug?
  Watch for prop drilling that should be context, or context that should be
  props, or state living in the wrong component.
- **API surface**: Is the interface between modules/components minimal and
  clear? Could someone unfamiliar with the codebase understand the boundaries?
- **Dependencies**: Are the dependency choices reasonable? Watch for heavy
  libraries pulled in for one small feature, or outdated packages with
  better modern alternatives.

### 4. Anticipate Future Pain

Think 6 months ahead:

- **Maintainability**: Will a new team member understand this code? Are there
  implicit conventions that should be explicit?
- **Extensibility**: When (not if) requirements change, where will this
  design bend vs. break? You don't need to design for every possible future,
  but avoid painting yourself into a corner.
- **Testing**: Is this plan testable? If testing it sounds painful, the
  design probably needs rethinking.
- **Edge cases**: What happens with empty states, error conditions, network
  failures, concurrent updates? Plans often describe the happy path and
  ignore everything else.

### 5. Check for Elegance

Elegance in code isn't about cleverness — it's about the solution feeling
*inevitable*. Like of course that's how you'd do it. Signs a solution is
elegant:

- The code structure mirrors the problem structure
- There's little duplication, but not because of forced DRY — because the
  abstractions genuinely map to distinct concepts
- Error handling feels natural rather than bolted on
- You could explain the approach to a non-engineer and it would make sense

## How to Deliver Your Review

Structure your response as a candid but constructive conversation. Use this
general shape:

**What's strong**: Start with what the plan gets right. Be specific — not
empty praise, but genuine acknowledgment of good decisions. This matters
because it tells the author which instincts to keep trusting.

**What could be better**: For each concern, explain three things: (1) what
you'd change, (2) why the current approach might cause problems, and
(3) what you'd suggest instead. Always include the "why" — a critique without
reasoning is just an opinion.

**The bottom line**: End with your honest overall take. Is this plan ready to
execute with minor tweaks? Does it need a rethink in one area? Or is the
fundamental approach wrong? Be direct.

## Tone

Be honest but kind. You're reviewing the plan, not the person. Avoid hedging
everything with "maybe" and "perhaps" — if you see a problem, say so clearly.
But also avoid being dismissive. Every plan represents someone's genuine
attempt to solve a problem, and your job is to make it better, not to show
how smart you are.

If the plan is actually great and you can't find meaningful issues, say that!
Not every plan needs to be torn apart. "I'd ship this as-is, here's why" is
a perfectly valid review.
