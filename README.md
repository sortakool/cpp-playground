# cpp-playground

Latest-tool and latest-kernel C++ development environment with a Python control plane, a Linux `amd64` devcontainer, and explicit low-level kernel validation lanes.

## Baselines

- Node `v25.8.1` on the current/latest release channel
- Linux latest-stable kernel on the selected proof surface
- LLVM `22.1.1`
- GCC `15.2.0`
- `mise` `2026.3.10`
- `uv` `0.10.12`
- `pixi` `0.66.0`
- GitHub CLI `2.88.1`
- Codex CLI `0.116.0`
- Claude Code `2.1.81`
- Gemini CLI `0.34.0`
- `just` `1.47.1`
- `chezmoi` `2.70.0`
- `watchexec` `2.5.0`
- `include-what-you-use` `0.25` in the Linux `llvm-stable` pixi environment

## Execution Surfaces

- `devcontainer`: daily Linux `amd64` userspace environment with exact tool pins and reflection lanes.
- `latest-kernel-vm`: local interactive Linux VM on the latest-stable kernel for low-level validation.
- `latest-kernel-ci`: self-hosted Linux `amd64` CI runner on the same latest-kernel policy.

## Apple Silicon Host Caveat

- The repo's devcontainer proof path is pinned to `linux/amd64`; it is not a first-class `linux/arm64` surface today.
- On Apple Silicon, Docker Desktop reaches `linux/amd64` through emulation. That path is not a supported proof surface for the `llvm-tsan` lane because ThreadSanitizer can fail under emulation before repo code runs.
- If `mise run prove-devcontainer` fails with `ThreadSanitizer: memory layout is incompatible` and the failing process maps `/run/rosetta/rosetta`, treat that as the Apple Silicon emulation caveat tracked in [issue #1](https://github.com/sortakool/cpp-playground/issues/1), not as evidence that the repo's native Linux `amd64` TSan lane is broken.
- For end-to-end devcontainer proof, prefer a native Linux `amd64` Docker host or VM.

## Control Plane

- `mise run refresh`: query upstreams, rewrite exact pins, and refresh lockfiles.
- `mise run sync-generated`: synchronize derived cross-file pins from the native checked-in config without querying upstreams.
- `mise run check-cpp26-toolchain-pins`: compare the pinned clang/gcc reflection refs with the upstream `p2996` and `reflection` branch heads.
- `mise run bump-cpp26-toolchain-pins`: refresh the pinned clang/gcc reflection refs and regenerate the derived files.
- `mise run build-cpp26-images`: build the repo base, the clang/gcc artifact images, and the exported final base from the root `docker-bake.hcl`; use `uv run -m tooling build-cpp26-images --toolchain ... --flavor ...` for non-default selections.
- `mise run build-devcontainer-image`: build the full graph through the final devcontainer image with the current host short username.
- `mise run bootstrap`: install the locked pixi environment, install repo-pinned `mise` tools without loading host-global `mise` config, sync the uv-managed Python dev environment, and install repo-managed helper CLIs.
- `mise run validate-repo`: verify committed config stays aligned with the native checked-in files and native tool metadata.
- `mise run validate-docker-images`: validate the locally built repo base, compiler artifact, final base, and devcontainer images with image-specific binary/version/path/native-tool checks.
- `mise run validate-runtime`: run native tool verification commands first, then verify installed versions match the native checked-in pins.
- `mise run validate-all`: run both repo and runtime validation.
- `mise run prove-devcontainer`: run the locked userspace/toolchain matrix.
- `mise run prove-latest-kernel-vm`: run the latest-kernel validation suite locally.
- `mise run prove-latest-kernel-ci`: run the same kernel-sensitive suite on the CI runner.

## Validation Policy

- Prefer each tool's native validation or inspection command before repo-specific checks.
- `mise run validate-runtime` starts with `mise doctor`, `pixi info`, `uv tool list`, and `docker buildx inspect`.
- `mise run validate-docker-images` checks each locally built image layer for the right binaries, version strings, filesystem paths, and native tool smoke commands before the devcontainer is used.
- Python quality gates run through `uv run` inside the project; pixi tasks are wrappers around the repo-owned uv environment.
- Prefer existing `mise` registry aliases such as `claude-code` and `gemini-cli` before backend-qualified selectors like `npm:` or `github:`.
- Repo control-plane `mise` operations isolate themselves from `~/.config/mise` so repo lock refreshes do not rewrite the host-global `mise.lock` or inherit host hooks by default.
- Repo validation fails if any file in the working tree still contains the legacy hardcoded shared-user token.

## Phase 0 Review Gate

- Run `mise run install-phase0-review-skills` once to install the local `adversarial-thinking`, `code-doubter`, and `adversarial-committee` rubrics used by the gate.
- Run `mise run review-plan-phase0-dry-run` to write the Phase 0 prompts, readiness report, and repo context without invoking Claude or Gemini.
- Run `mise run review-plan-phase0` to execute the adversarial review gate against the checked-in migration plan.
- The gate writes artifacts under `.codex/plan-reviews/<slug>/`, including the input plan, readiness checks, per-model reviews, cross-examinations, and the merged synthesis.
- The gate loads rubric excerpts from the installed local skill files under `.agents/skills` or `.codex/skills`, then executes the review with the pinned local `claude` and `gemini` CLIs.
- If the required local rubrics are missing, `mise run review-plan-phase0` fails fast and points back to `mise run install-phase0-review-skills`.
- The checked-in migration plan lives in [spec/2026-03-22-chezmoi-mise-devcontainer-migration-plan.md](spec/2026-03-22-chezmoi-mise-devcontainer-migration-plan.md).

## Mac Devcontainer Parity

- The primary devcontainer user tracks the host short username. Rebuild the image on each host with `mise run build-devcontainer-image` before creating the container.
- Host-side machine setup belongs in `chezmoi`; repo-owned CLI pins and environment policy belong in `mise`.
- Use the authoritative onboarding guide in [docs/mac-devcontainer-parity.md](docs/mac-devcontainer-parity.md) for SSH-agent, host-local SSH login, GitHub CLI, and local-secrets workflows on macOS.

## Tooling Split

- Python control plane owns upstream resolution, validation, and orchestration.
- The checked-in Docker/devcontainer/image files are canonical and edited in place: [docker-bake.hcl](docker-bake.hcl), [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json), [.devcontainer/Dockerfile](.devcontainer/Dockerfile), and [tooling/cpp26-dev-images/](tooling/cpp26-dev-images/).
- The root `docker-bake.hcl` owns the `repo_base`, compiler-artifact, `final_base`, and devcontainer targets so lineage and `linux/amd64` stay aligned.
- `chezmoi` owns host-scoped source state only, rooted at `home/` through `.chezmoiroot`; it must never manage repo-generated files.
- The Python control plane validates and synchronizes derived values, but the checked-in native files remain the source of truth.
- `mise` is the documented public interface and manages exact fast-moving CLIs.
- `pixi` owns the stable helper environments: `llvm-stable`, `gcc-stable`, and `toolchains-stable`.
- Image-managed exceptions are limited to `gcc-reflection` and `clang-p2996`.

## Kernel Coverage

The Linux kernel validation surface includes dedicated tests for:

- shared memory via `memfd` and POSIX `shm`
- `epoll`
- `io_uring`
- eBPF map operations

Each test prints numeric evidence and returns non-zero on unsupported or misconfigured host behavior.

## Bootstrap

1. Build or refresh the wrapper image:

   ```bash
   mise run build-devcontainer-image
   ```

2. Open the repo as a devcontainer.

3. Bootstrap the locked user-space tools:

   ```bash
   mise run bootstrap
   ```

4. Validate the checked-in state:

   ```bash
   mise run validate-all
   mise run validate-docker-images
   ```

5. Authenticate GitHub CLI once inside the container, then run the parity smoke:

   ```bash
   gh auth login --git-protocol ssh
   mise run smoke-ssh-git-gh-parity
   ```

6. For host-local SSH login into the devcontainer on macOS:

   ```bash
   mise run devcontainer-up-macos
   mise run sync-devcontainer-ssh-known-hosts
   mise run smoke-ssh-into-devcontainer
   ssh -p 2222 "${USER}@127.0.0.1"
   ```

7. For kernel-sensitive work, use the VM/runner flow documented in [docs/latest-kernel-testing.md](docs/latest-kernel-testing.md).
