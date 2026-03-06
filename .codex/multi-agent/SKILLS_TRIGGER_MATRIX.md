# Skills Trigger Matrix

## Standardized skills

| Prompt intent | Skill(s) | Invocation policy |
|---|---|---|
| Build/refresh C++26 reflection images | `cpp26-dev-image-build` | Implicit allowed |
| Validate reflection/sanitizer image health | `cpp26-dev-image-validate` | Implicit allowed |
| Publish/retag/sync image artifacts | `cpp26-dev-image-publish` | Explicit-only |
| OpenAI/Codex product behavior/config questions | `openai-docs` | Implicit allowed |
| Multi-agent orchestration guidance | `parallel-agents` | Implicit allowed |
| Execute independent implementation tasks with sub-agents | `subagent-driven-development` | Implicit allowed |
| Completion/health claims before handoff | `verification-before-completion` | Mandatory quality gate |
| Create/update skills | `skill-creator` | Implicit when skill editing is requested |

## Negative checks

- Build/validate prompts must not trigger publish behavior.
- Publish operations must require explicit user intent.
- OpenAI docs requests must use official docs sources before general web search.
