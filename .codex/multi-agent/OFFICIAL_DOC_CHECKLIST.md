# Official OpenAI Docs Checklist (Codex Multi-Agent)

## Version and visibility

- Compare versions:
  - `codex --version`
  - `/Applications/Codex.app/Contents/Resources/codex --version`
- Multi-agent visibility is currently CLI-first; App/IDE visibility may lag.

## Required config keys

- `features.multi_agent = true`
- `[agents]`:
  - `max_threads`
  - `max_depth`
  - `job_max_runtime_seconds`
- Per role:
  - `agents.<name>.description`
  - `agents.<name>.config_file`

## Telemetry keys

- `[otel]`:
  - `environment`
  - `log_user_prompt`
  - `exporter`
  - `trace_exporter`
- Exporter fields (as needed): endpoint/protocol/headers/tls

## References

- https://developers.openai.com/codex/multi-agent
- https://developers.openai.com/codex/concepts/multi-agents
- https://developers.openai.com/codex/config-reference
- https://developers.openai.com/codex/config-basic
- https://developers.openai.com/codex/config-advanced
- https://developers.openai.com/codex/app/troubleshooting/#feature-is-working-in-the-codex-cli-but-not-in-the-codex-app
