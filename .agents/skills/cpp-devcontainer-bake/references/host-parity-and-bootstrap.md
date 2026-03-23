# Host Parity And Bootstrap

Use this note when the task touches host bootstrap, username parity, SSH-agent forwarding, or devcontainer runtime hooks.

## Ownership Split

- `home/` with `chezmoi` `dot_` naming: host bootstrap and host-scoped config state.
- root `Dockerfile` + `docker-bake.hcl`: image and stage topology.
- `.devcontainer/devcontainer.json`: runtime wiring and hook invocation.
- minimal Python helpers: bootstrap finalization, verification, and devcontainer runtime helpers.

Do not collapse these layers into one command or one file.

## User And SSH Contract

- Devcontainer user remains dynamic and host-aligned.
- SSH runtime helper behavior remains enabled in container lifecycle hooks.
- Host SSH agents are forwarded without copying private keys.
- On macOS with Docker Desktop, do not expect a bind-mounted host UNIX socket to work directly inside the Linux container. The checked-in flow is:
  - host launchd SSH socket -> host-local TCP proxy under `~/.local/state/cpp-playground/`
  - `host.docker.internal:<port>` -> container-local UNIX socket `/tmp/cpp-playground-ssh-agent.sock`
- `gh` token parity is not part of the SSH contract. Host `gh` auth may be backed by the macOS keychain and stay unavailable inside the container.

## Bootstrap And Verify

Use:

```bash
./install.sh
uv run finalize-bootstrap
uv run verify run
```

Do not replace this with legacy control-plane flows.

For SSH-specific validation after lifecycle or runtime changes, use:

```bash
python3 -m cpp_playground.devcontainer_runtime smoke-ssh
```

On macOS hosts whose current shell does not export `SSH_AUTH_SOCK`, wrap host-side checks with:

```bash
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh-add -l
SSH_AUTH_SOCK="$(launchctl getenv SSH_AUTH_SOCK)" ssh -T git@github.com
```

## Security Notes

- Keep non-root runtime user defaults.
- Do not mount host `~/.ssh`, host credential stores, or full host `$HOME`.
- Do not store long-lived tokens in devcontainer config.
