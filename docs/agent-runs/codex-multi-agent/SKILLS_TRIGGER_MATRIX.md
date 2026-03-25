# Skills Trigger Matrix

## Standardized skills

| Prompt intent | Skill(s) | Invocation policy |
|---|---|---|
| local-only core dev image build + validate orchestration (clang required, gcc optional) | `cpp26-dev-image-build` + `cpp26-dev-image-validate` | Implicit allowed |
| Build/refresh C++26 reflection images | `cpp26-dev-image-build` | Implicit allowed |
| Validate reflection/sanitizer image health | `cpp26-dev-image-validate` | Implicit allowed |
| telemetry verification thread for MA evidence windows | `verification-before-completion` | Mandatory quality gate |
| Final local dev acceptance gate execution | `verification-before-completion` | Mandatory quality gate |
| Publish/retag/sync image artifacts | `cpp26-dev-image-publish` | explicit-only |
| OpenAI/Codex product behavior/config questions | `openai-docs` | Implicit allowed |
| Multi-agent orchestration guidance | `parallel-agents` | Implicit allowed |
| Execute independent implementation tasks with sub-agents | `subagent-driven-development` | Implicit allowed |
| Completion/health claims before handoff | `verification-before-completion` | Mandatory quality gate |
| Create/update skills | `skill-creator` | Implicit when skill editing is requested |

## Negative checks

- Build/validate prompts must not trigger publish behavior.
- Build/validate language (including release-adjacent phrasing) must not trigger publish behavior.
- Publish operations must require explicit user intent.
- OpenAI docs requests must use official docs sources before general web search.
- quantlib requests are out-of-scope in this MA-05..MA-09 wave.

## Intent Boundary Checks (False Trigger Control)

| Prompt example | Expected skill route | Boundary rationale |
|---|---|---|
| "Build the latest clang reflection image and run sanitizer smoke tests." | `cpp26-dev-image-build` + `cpp26-dev-image-validate` | Build + validate language only; no publish verbs present. |
| "Retag and push the clang image to GHCR." | `cpp26-dev-image-publish` only | Contains explicit publish verbs (`retag`, `push`). |
| "Can you verify the image is healthy before release?" | `cpp26-dev-image-validate` | "Before release" alone is not publish intent. |
| "Publish if tests pass." | Block for explicit confirmation before `cpp26-dev-image-publish` | Conditional publish is still destructive; require explicit user confirmation in-thread. |
| "How do Codex AGENTS.md precedence rules work?" | `openai-docs` | Product/docs question; should not route to local image skills. |
| "Split this work into sub-agents and execute independent tasks." | `parallel-agents` + `subagent-driven-development` | Explicit orchestration + execution request. |
