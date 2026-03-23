# Host Parity And Bootstrap

Use this note when the task involves host bootstrap, user parity, SSH-agent forwarding, `gh` auth, or the split between `chezmoi`, `mise`, `pixi`, and the devcontainer hooks.

## Ownership Split

- `chezmoi`: host bootstrap, shell setup, and host-local machine configuration
- `mise.toml`: repo-owned CLI pins and env redaction rules
- `mise.local.toml`: gitignored local-only overrides and secrets
- `pixi.toml`: locked repo environments and named tasks
- `.devcontainer/Dockerfile`: baked-in toolchain and runtime dependencies
- `.devcontainer/devcontainer.json`: runtime wiring, mounts, `remoteUser`, `postCreateCommand`, `postStartCommand`
- `tooling/control_plane.py`: orchestration and validation

Do not collapse these layers into one file or one command.

## Host Username Parity

The primary container user tracks the host short username.

That design affects:

- the image build
- `remoteUser`
- named-volume mount targets under `/home/${localEnv:USER}`
- host-local SSH login on `127.0.0.1:2222`
- post-create validation

If the container user and `CPP_PLAYGROUND_HOST_USER` diverge, `python3 -m tooling post-create` fails and explicitly tells the caller to rebuild the image on the host.

## macOS CLI Path

Canonical host-side CLI flow:

```bash
python3 -m tooling build-devcontainer-image
python3 -m tooling host-preflight-macos
python3 -m tooling devcontainer-up-macos
python3 -m tooling sync-devcontainer-ssh-known-hosts
python3 -m tooling smoke-ssh-into-devcontainer
ssh -p 2222 "${USER}@127.0.0.1"
```

`devcontainer-up-macos` mounts Docker Desktop's host-services SSH socket and sets `SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock` inside the container.

## Editor Path

For VS Code or CLion devcontainer flows:

- build the image first
- let the editor handle container creation and SSH-agent integration
- rely on the same checked-in `postCreateCommand` and `postStartCommand`
- run the same in-container smoke checks after attach

Do not create a second editor-specific bootstrap path unless the user is intentionally changing the product workflow.

## In-Container Hooks

`postCreateCommand`:

- runs `python3 -m tooling post-create`
- ensures home-directory mounts exist for the current user
- seeds GitHub SSH host keys
- runs `bootstrap()`

`postStartCommand`:

- runs `python3 -m tooling ensure-devcontainer-ssh`
- manages container SSH host keys
- syncs `authorized_keys` from `ssh-add -L` when the host agent is available
- starts `sshd`

Prefer these checked-in hooks over ad-hoc shell scripts.

## Secrets And Auth

Preferred options:

- gitignored `mise.local.toml`
- `doppler run -- ...` for short-lived secret injection

Do not:

- mount host `~/.ssh`
- mount host credential stores
- mount host `$HOME`
- store long-lived tokens in `devcontainer.json`

`gh` auth persists in the named `gh-config` volume under `/home/${USER}/.config/gh`.

## Best-Practice Adaptation

Reviewed generic devcontainer skills commonly recommend:

- root users
- blanket bind mounts of host config
- generated `docker-compose.yml`
- large `setup.sh` scripts for all tooling

For this repo, the better adaptation is:

- non-root host-username parity
- named volumes for agent tool homes and caches
- SSH-agent socket forwarding instead of key copying
- baked-in durable toolchain content
- post-create bootstrap for repo state
- post-start startup for SSH service state
