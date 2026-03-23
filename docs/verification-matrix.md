# Verification Matrix

`uv run verify run` executes the declarative suites in [verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml). `uv run verify run --json` emits the same results as structured JSON.

## Cleanup / Regression

- `cleanup.one-dockerfile`: the tracked Dockerfile surface is limited to the repo-root `Dockerfile` plus the thin `.devcontainer/Dockerfile.host-user` overlay.
- `cleanup.no-control-plane`: the old `tooling/` control plane, split Dockerfiles, and chezmoi script directory are gone.
- `cleanup.no-generated-artifacts`: bytecode, egg-info, and ad-hoc log files are no longer tracked.
- `cleanup.chezmoi-dot-naming`: managed targets under `home/` use chezmoi `dot_` naming.
- `cleanup.no-duplicate-orchestration`: `mise.toml`, `pixi.toml`, and `pyproject.toml` do not reintroduce the old orchestration verbs.

## Image Graph

- `image.stage-names.exact`: the root Dockerfile exposes `base`, `clang`, `gcc`, `final`, and `devcontainer` in order.
- `image.bake-targets`: `docker-bake.hcl` exposes the expected targets and groups.
- `image.bake-print.devcontainer`: resolved Bake output still points at the single root `Dockerfile`.
- `image.bake-native-check`: `docker buildx bake --check` passes for `base`, `clang`, `gcc`, `final`, and `devcontainer`.
- `image.dockerfile-hadolint`: `hadolint` accepts the root Dockerfile under the repo's snapshot-pinned package policy.
- `image.parallel-toolchains`: `clang` and `gcc` remain sibling stages from `base`.
- `image.repo-bootstrap-after-toolchains`: repo copy and bootstrap stay scoped to `final`, so devcontainer/runtime edits do not force toolchain rebuilds.
- `image.final.includes-both-toolchains`: `final` materializes both reflection toolchains.

## Bootstrap

- `bootstrap.install-entrypoint`: `install.sh` and the chezmoi-rendered `mise` bootstrap stay present and non-interactive, and bootstrap helpers use system `python3` instead of pinning Python through `mise`.
- `bootstrap.python-surface`: the Python package remains limited to the narrow helper modules.
- `bootstrap.console-scripts`: `pyproject.toml` only exposes `devcontainer-runtime`, `finalize-bootstrap`, and `verify`.

## Devcontainer

- `devcontainer.runtime-hooks`: `postCreateCommand` and `postStartCommand` stay on the thin runtime helper module.
- `devcontainer.host-user-and-ssh-wiring`: the initialize step uses the thin host-user overlay, publishes the macOS SSH agent through a host-local TCP proxy recorded in host state, and keeps host username parity plus a stable in-container forwarded agent socket at `/tmp/cpp-playground-ssh-agent.sock`.
- `devcontainer.image-reference`: `.devcontainer/devcontainer.json` uses the fully-qualified first Bake tag instead of a short local alias.
- `devcontainer.from-final`: `devcontainer` still derives directly from `final`.
- `devcontainer.runtime-packages-only`: the wrapper stage only installs runtime support packages.

## Docs / Skills

- `docs.no-legacy-build-surface`: README, docs, repo skills, and repo instructions no longer point at the deleted control-plane or split-Dockerfile layout.
