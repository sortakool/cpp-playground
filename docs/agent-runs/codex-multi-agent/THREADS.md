# Codex App Multi-Agent Thread Split

This workspace uses an App + CLI hybrid control plane:
- Codex App: thread orchestration, review, and handoff
- Codex CLI: live sub-agent visibility, approvals, and low-level debugging

## Threads

1. `MA-00 Session Open Items`
- Fix OTEL forwarding path issues, verify collector health, verify prompt telemetry posture.
- Owner role: `worker`; monitor role: `monitor`.

2. `MA-01 Runtime Baseline`
- Validate effective global/project config precedence and role coherency.
- Roles: `explorer`, `reviewer`.

3. `MA-02 Role Topology`
- Finalize task-class dispatch policy for context-rot control.
- Roles: `docs_researcher`, `reviewer`.

4. `MA-03 Skills Trigger Matrix`
- Validate trigger intents, implicit/explicit invocation policy, and false-trigger boundaries.
- Roles: `explorer`, `reviewer`.

5. `MA-04 Strict Validation Gate`
- Run binary PASS/FAIL gate covering config, agent tools, policy, and telemetry.
- Roles: `worker`, `monitor`, `reviewer`.

6. `MA-05 Environment + Team Bootstrap`
- Verify build prerequisites and establish telemetry/log evidence baseline for the MA-05..MA-09 execution window.
- Roles: `worker`, `monitor`.

7. `MA-06 Build Core Dev Images`
- Build local core dev images via canonical build script with clang required and gcc optional.
- Roles: `worker`, `monitor`.

8. `MA-07 Validate Core Dev Images`
- Validate local core dev images via canonical validation script with clang required and gcc optional.
- Roles: `worker`, `reviewer`.

9. `MA-08 Telemetry/Log Verification`
- Verify telemetry/log evidence for MA-05..MA-07 runtime windows.
- Roles: `monitor`, `reviewer`.

10. `MA-09 Final Dev Acceptance Gate`
- Run final binary acceptance gate for local dev images and telemetry stability.
- Roles: `worker`, `reviewer`.

11. `MA-10 Build GCC Core Dev Image`
- Build local GCC core dev image via canonical build script.
- Roles: `worker`, `monitor`.

12. `MA-11 Validate GCC Core Dev Image`
- Validate local GCC core dev image via canonical validation script.
- Roles: `worker`, `reviewer`.

13. `MA-12 Final GCC Acceptance`
- Run final binary acceptance gate with `--require-gcc`.
- Roles: `worker`, `reviewer`.

14. `MA-13 Build Optimization Baseline`
- Read the devcontainer build optimization spec, map repo invariants, and produce the integration checklist for the wave.
- Roles: `explorer`, `reviewer`.

15. `MA-14 Authoritative Smoke Gate`
- Implement the authoritative Linux `amd64` devcontainer smoke workflow and repo-owned smoke script.
- Roles: `worker`, `monitor`.

16. `MA-15 Benchmark Surface`
- Implement the benchmark schema, benchmark scripts, size-report script, and pixi task surface for measured build/image comparisons.
- Roles: `worker`, `reviewer`.

17. `MA-16 Verification + Docs Integration`
- Extend verification for pin/schema alignment and document the new command surface without broadening repo contracts.
- Roles: `worker`, `reviewer`.

18. `MA-17 Constrained Optimization Experiment`
- Land only optimization changes that fit the spec's V1 scope and are backed by repo-owned measurement.
- Roles: `worker`, `monitor`, `reviewer`.

19. `MA-18 Adversarial Final Acceptance`
- Run adversarial review against the spec and current repo contracts, then produce the final PASS/FAIL with blockers and follow-ups.
- Roles: `reviewer`, `worker`.

## Execution order

Run `MA-00` first. Then `MA-01` and `MA-02` can run in parallel. `MA-03` follows once runtime baseline is stable. `MA-04` is final acceptance.

For the dev-image wave, run `MA-05` first, then `MA-06`, then `MA-07`, then `MA-08`, then `MA-09` as strict sequential acceptance.

For the gcc-completion wave, run `MA-10`, then `MA-11`, then `MA-12` as strict sequential acceptance.

For the build-optimization wave, run `MA-13` first. Then `MA-14`, `MA-15`, and `MA-16` can run in parallel once the baseline and write scopes are fixed. Run `MA-17` after those three land. Run `MA-18` last as the adversarial acceptance gate.

## Thread completion contract

Each thread must return:
- Findings summary (3-10 bullets)
- Exact evidence commands used
- PASS/FAIL for its done criteria
- Open blockers and owner thread
