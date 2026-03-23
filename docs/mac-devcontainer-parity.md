# Mac Devcontainer Notes

This repository no longer documents a separate macOS-host command flow for devcontainer lifecycle management.

## Current Contract

- The authoritative devcontainer proof surface is Linux `amd64`.
- The devcontainer remains a thin runtime wrapper over the `final` image stage.
- Dynamic host username parity and SSH runtime helpers remain part of the checked-in devcontainer behavior.
- On macOS with Docker Desktop, SSH agent forwarding is implemented as a host-local TCP proxy recorded under `~/.local/state/cpp-playground/ssh-agent-port` plus a stable in-container UNIX socket at `/tmp/cpp-playground-ssh-agent.sock`.
- Legacy control-plane and mac-host orchestration commands are no longer part of the documented interface.

## What To Use Instead

- Use root `Dockerfile` + `docker buildx bake` as the build interface.
- Use `./install.sh` and `uv run finalize-bootstrap` for bootstrap.
- Use `uv run verify run` for verification.
- For Apple Silicon caveats and proof expectations, use [docs/apple-silicon-devcontainer-amd64-emulation.md](docs/apple-silicon-devcontainer-amd64-emulation.md).

## SSH Validation Notes

- Validate SSH parity with:
  - `SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh-add -l`
  - `python3 -m cpp_playground.devcontainer_runtime smoke-ssh`
- Do not require `gh auth status` parity inside the container as proof of SSH parity. Host `gh` auth may be backed by the macOS keychain and intentionally not available inside the Linux container.
- If host access to `127.0.0.1:2222` reports a changed host key after recreating the devcontainer, refresh the local entry with:

```bash
ssh-keygen -R '[127.0.0.1]:2222'
```

- If the current macOS shell does not export `SSH_AUTH_SOCK`, wrap host-side SSH commands with:

```bash
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh -p 2222 rmanaloto@127.0.0.1
```
