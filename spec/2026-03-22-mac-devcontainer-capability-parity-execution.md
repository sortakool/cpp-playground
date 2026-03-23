# Mac Devcontainer Capability Parity Execution Plan

## Summary

This plan defines how to make the repository's Linux devcontainer feel equivalent to working directly on a macOS host for daily development, without pretending a Linux container can literally become the macOS account.

The implementation target is capability parity, not identity parity:

- Keep the primary container user aligned to the host short username instead of a hardcoded shared Linux account.
- Keep Git transport SSH-only.
- Reuse the host SSH agent safely instead of copying private keys.
- Provide equivalent in-container GitHub CLI access.
- Provide equivalent environment-variable and secrets workflows using host-side `chezmoi`, repo-side `mise`, and optional Doppler integration.
- Keep `/var/run/docker.sock` mounted by default because that was explicitly requested.

This plan is intended to be executable by a fresh Codex session and a subagent-oriented SDLC workflow.

## Explicit Decisions

- The repository remains Linux `amd64` devcontainer-first.
- The primary container user should match the host short username (for macOS, the account short name) instead of remaining a hardcoded shared user.
- `updateRemoteUserUID` remains enabled for bind-mount ergonomics only.
- Do not mount host `~/.ssh`, host credential stores, or host `$HOME` into the container.
- Do not attempt to mirror macOS Keychain-backed GitHub session state into Linux.
- Add `gh` to the repo-managed CLI layer.
- Persist GitHub CLI auth in a container volume at `/home/${localEnv:USER}/.config/gh`.
- Support VS Code Dev Containers, `devcontainer` CLI, and CLion. Do not rely on VS Code-only credential-sharing behavior as the portable mechanism.
- Keep `docker.sock` mounted by default, but document that this is effectively host-level container control.

## Constraints And Non-Goals

- True macOS account privilege equivalence is not achievable inside a Linux container on Docker Desktop for Mac.
- UID/GID alignment is not a substitute for macOS ACL, Keychain, TCC, or SIP behavior.
- The goal is practical development parity for SSH, GitHub CLI, and environment/secrets workflows.
- Commit-signing parity is out of scope unless it falls out naturally from the supported editor/tooling path.

## Current Repo Surfaces To Modify

- `.devcontainer/devcontainer.json`
- `.devcontainer/Dockerfile`
- `uv run -m tooling post-create`
- `mise.toml`
- `tooling/control_plane.py`
- `tooling/tool-version-manifest.json`
- `.devcontainer/devcontainer.json`
- `docker-bake.hcl`
- `tooling/cpp26-dev-images/`
- `README.md`
- `docs/`

Add new files if needed under:

- `tooling/`
- `docs/`
- optionally `scripts/` for host-side helper entrypoints

## Required Behavior

### 1. SSH parity

- The container must be able to use the host's loaded SSH identities through the SSH agent.
- The container must not contain copied host private keys.
- GitHub SSH access must work without interactive host-key prompts after setup.
- The repository's existing SSH remote must work from inside the container.
- The same setup must be usable from:
  - VS Code Dev Containers
  - CLion Dev Containers
  - `devcontainer` CLI on macOS

### 2. GitHub parity

- `gh` must be available as part of the repo-managed toolchain.
- A developer must be able to run `gh auth login --git-protocol ssh` once inside the container.
- `gh auth status` must remain valid across rebuilds/reattach for the same devcontainer volume set.
- Git transport remains SSH-only even when `gh` is used.

### 3. Environment and secrets parity

- Host-side environment/bootstrap guidance must use `chezmoi` for machine-specific setup and dotfiles.
- Repo-owned environment contract must use `mise`.
- Sensitive variables must support redaction in `mise`.
- Missing required variables must fail clearly.
- Doppler must be documented as the preferred optional path for equivalent secrets delivery into the container without copying host secret files.
- Existing direct `${localEnv:...}` passthrough in `devcontainer.json` must be reviewed and reduced to startup-critical variables only.

## SDLC Multi-Agent Team

### Orchestrator

Responsibilities:

- Create an isolated worktree and feature branch before implementation.
- Use a fresh implementer subagent per task or task batch.
- Enforce review order:
  - spec compliance review first
  - code quality review second
- Integrate the resulting changes.
- Run final validation and summarize remaining risk.

Required branch setup:

- Base branch: `codex/devcontainer-tooling-foundation`
- New branch: `codex/mac-devcontainer-parity`
- Preferred worktree path: `.worktrees/mac-devcontainer-parity`

### Implementer A: Container/Auth plumbing

Write scope:

- `.devcontainer/devcontainer.json`
- `.devcontainer/scripts/`
- any small helper shell scripts specifically for parity/preflight

Responsibilities:

- Add editor-neutral SSH-agent parity support.
- Add a macOS host preflight helper.
- Add a `devcontainer` CLI launch path for Docker Desktop host-services SSH socket.
- Add GitHub `known_hosts` bootstrap or equivalent deterministic SSH trust setup.
- Add parity smoke scripts for SSH and Git.

### Implementer B: Toolchain/GitHub CLI

Write scope:

- `mise.toml`
- `tooling/tool-version-manifest.json`
- `tooling/control_plane.py`
- template/config validation code as needed

Responsibilities:

- Add `gh` to the managed CLI layer.
- Extend bootstrap/validation to recognize `gh`.
- Persist `gh` auth using a named devcontainer volume.
- Add explicit validation for `gh auth status`.

### Implementer C: Env/Secrets/Docs

Write scope:

- `README.md`
- `docs/`
- optional example or helper docs under `docs/`

Responsibilities:

- Document host-side `chezmoi` usage.
- Document repo-side `mise` env contract and local overlays.
- Document Doppler-backed optional secret injection path.
- Document differences between VS Code, CLion, and `devcontainer` CLI.
- Document the security model and limitations.

### Reviewer 1: Spec compliance

Must reject:

- any host `~/.ssh` mount
- any host credential-store mount
- any host `$HOME` mount
- any design that keeps a hardcoded shared primary user instead of the host short username
- any design that depends only on VS Code extension magic

### Reviewer 2: Code quality

Must verify:

- repo conventions are followed
- generated/template surfaces stay in sync
- helper scripts are minimal and deterministic
- validation commands cover the new behavior

### Final reviewer

Must verify:

- the whole branch matches the approved plan
- no stray auth/secrets shortcuts slipped in
- docs and validation cover the new workflow end-to-end

## Execution Waves

### Wave 0: Workspace isolation and baseline

Tasks:

- Create `.worktrees/` if missing.
- If `.worktrees/` is not ignored, add it to `.gitignore` first.
- Create the new worktree and branch from `codex/devcontainer-tooling-foundation`.
- Capture a clean baseline with:
  - `git status --short`
  - `pixi run validate-repo`
  - `pixi run validate-runtime`

Acceptance:

- Clean baseline recorded.
- No unrelated changes in the new worktree.

### Wave 1: Core SSH parity

Tasks:

- Add a host preflight check for macOS that validates:
  - Docker Desktop is available
  - `SSH_AUTH_SOCK` exists on host
  - `ssh-add -l` succeeds on host
  - repo remote uses SSH
- Add editor-neutral SSH parity support:
  - VS Code and CLion use their documented SSH-agent support when present
  - `devcontainer` CLI path explicitly binds `/run/host-services/ssh-auth.sock` and exports `SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock`
- Add deterministic GitHub SSH trust bootstrap inside the container.
- Add a parity smoke command that runs:
  - `ssh-add -l`
  - `ssh -T git@github.com`
  - `git ls-remote origin`

Acceptance:

- A macOS user with a loaded host SSH agent can use GitHub SSH from inside the container.
- No host key material is copied into the container.

### Wave 2: GitHub CLI parity

Tasks:

- Add `gh` to `mise.toml`.
- Add version/pin support in `tooling/tool-version-manifest.json`.
- Extend `tooling/control_plane.py` bootstrap and validation so `gh` is part of runtime checks.
- Add a named volume mount for `/home/${localEnv:USER}/.config/gh`.
- Add post-create/post-start guidance or helper checks for:
  - `gh auth status`
  - `gh auth login --git-protocol ssh`

Acceptance:

- `gh` is installed by the normal repo toolchain bootstrap.
- `gh auth status` remains valid after rebuild/reattach using the same devcontainer volumes.

### Wave 3: Env/secrets parity

Tasks:

- Review every current `${localEnv:...}` passthrough in `devcontainer.json`.
- Keep only variables that truly must exist at container startup.
- Define repo-owned `mise` env requirements:
  - required variables
  - redactions
  - local overrides via gitignored local config
- Document or implement a `mise` local-secret pattern using `mise.local.toml`, `env._.file`, or equivalent repo-approved local overlay.
- Document Doppler-backed optional injection for local development:
  - preferred command shape
  - when to use `doppler run`
  - when a short-lived token handoff is acceptable
- Keep `chezmoi` as host provisioning guidance only:
  - shell init
  - `mise` activation
  - machine-specific templates
  - optional secret-manager glue

Acceptance:

- Required env vars fail clearly.
- Sensitive values are redacted in `mise` output/task logs.
- Secret files from the host are not mounted into the container.

### Wave 4: Documentation and security framing

Tasks:

- Add a single authoritative Mac onboarding doc.
- Explain the supported workflows for:
  - VS Code Dev Containers
  - CLion Dev Containers
  - `devcontainer` CLI
- Document limitations:
  - Linux container is not macOS identity parity
  - `docker.sock` grants strong host-level container control
  - primary Linux username tracks the host short username, but this still is not literal macOS identity parity
- Document anti-patterns:
  - mounting `~/.ssh`
  - mounting host credential stores
  - mounting host `$HOME`
  - embedding long-lived tokens in `devcontainer.json`

Acceptance:

- Another developer can follow docs and reach the validated parity state on macOS.

## Validation Commands

### Required automated validation

- `pixi run validate-repo`
- `pixi run validate-runtime`

Add or update repo validation so it also checks:

- `gh --version`
- parity helper/preflight scripts exist and are executable
- expected mounts/env for the CLI SSH-agent path exist in the generated config or documented wrapper flow

### Required parity smoke validation on macOS host

Host:

- `ssh-add -l`
- `git remote -v`

Container:

- `whoami`
- `ssh-add -l`
- `ssh -T git@github.com`
- `git ls-remote origin`
- `gh auth status`
- `mise env`

### Required manual acceptance

Run the same smoke validation through:

- VS Code Dev Containers
- CLion Dev Container support
- `devcontainer` CLI on macOS

## Security Guardrails

- Never mount host `~/.ssh` into the container.
- Never mount macOS Keychain or host Git credential stores into the container.
- Never mount host `$HOME` broadly.
- Never claim literal host privilege equivalence.
- Keep GitHub auth in the container independent from host Keychain-backed session state.
- Keep Doppler or other secret-manager integration optional and explicit.
- If a helper script prints environment variables, ensure sensitive values are redacted or omitted.

## Deliverables

The implementation is complete only when all of the following exist:

- Updated devcontainer config and templates
- `gh` in the repo-managed toolchain
- SSH/Git/GitHub parity smoke checks
- Host preflight helper for macOS
- Updated validation in `tooling/control_plane.py`
- Docs for VS Code, CLion, and `devcontainer` CLI
- Docs for `chezmoi` + `mise` + optional Doppler workflow
- Clear security caveats around `docker.sock`

## Handoff Notes For The Next Codex Session

The next session should announce that it is using:

- `using-git-worktrees`
- `executing-plans`
- `subagent-driven-development`

The next session should not re-plan from scratch. It should:

1. Create the isolated worktree.
2. Review this spec critically for contradictions.
3. Execute Wave 0 through Wave 4 in order.
4. Use spec review then code-quality review after each batch.
5. Finish with a full-branch review and branch-completion workflow.
