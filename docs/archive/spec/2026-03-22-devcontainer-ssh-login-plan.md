# Devcontainer SSH Login Plan

## Summary

- Goal: allow `ssh -p 2222 ${USER}@127.0.0.1` into the running devcontainer from the Mac host.
- Auth is fixed to key-only login using the host's existing SSH key identity and the same short username as the devcontainer user.
- Exposure is fixed to host-local only on `127.0.0.1`.
- Password auth, macOS password parity, and LAN exposure are out of scope.

## Implementation Changes

- Add `postStartCommand` in `.devcontainer/devcontainer.json` so the Python control plane configures and starts `sshd` on every container start.
- Publish a fixed host-local port with `127.0.0.1:2222:22`.
- Install `openssh-server` in the devcontainer runtime image only.
- Add `uv run -m tooling ensure-devcontainer-ssh` to create host keys, write a managed `sshd` drop-in, sync `authorized_keys` from `ssh-add -L`, and start `sshd` idempotently.
- Add `pixi run sync-devcontainer-ssh-known-hosts` on the host to refresh localhost SSH host-key trust for the current devcontainer.
- Add `pixi run smoke-ssh-into-devcontainer` on the host to verify `whoami == $USER` and `HOME=/home/$USER`.
- Keep the current host-short-username model unchanged. SSH login user remains the existing primary devcontainer user.

## Validation

- `pixi run validate-repo`
- `pixi run validate-runtime`
- `pixi run devcontainer-up-macos`
- `pixi run sync-devcontainer-ssh-known-hosts`
- `pixi run smoke-ssh-into-devcontainer`
- `pixi run smoke-ssh-git-gh-parity`
- `smoke-reflection`

## Assumptions

- The canonical proof target is macOS with Docker Desktop.
- Port `2222` is fixed in v1.
- The first key sync requires a container session that already has a usable `SSH_AUTH_SOCK`; the supported path for that is `pixi run devcontainer-up-macos`.
# Superseded

This archived spec is superseded by [docs/plans/2026-03-24-canonical-merged-plan.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plans/2026-03-24-canonical-merged-plan.md).
