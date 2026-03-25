# GitHub CI/CD Image Build Spec

## Summary

- Goal: add CI/CD that builds the repo's container images on GitHub-hosted runners, with a bias toward free GitHub-hosted capacity when the repository is public.
- Preserve the current repo contract:
  - one root `Dockerfile`
  - one thin `.devcontainer/Dockerfile.host-user` overlay
  - exact stage order `base`, `clang`, `gcc`, `final`, `devcontainer`
  - `devcontainer` derives from `final`
  - repo bootstrap remains in `final`
- Keep the current source-of-truth model:
  - `Dockerfile` owns stage graph and toolchain behavior
  - `docker-bake.hcl` owns tags, args, platforms, and cache settings
  - `verification/verification.toml` owns contract assertions
- Do not introduce a new control plane, generated manifest layer, or alternative image topology.
- This spec defines a hosted build-and-publish surface, not a change to the repo's authoritative proof policy unless explicitly approved in a later RFC.

## Why This Exists

- The repo already has a narrowed root-Dockerfile build surface and a V1 build-optimization plan.
- The current repo has:
  - a fast hosted integrity workflow: `.github/workflows/tooling-validate.yml`
  - a self-hosted latest-kernel workflow: `.github/workflows/latest-kernel-ci.yml`
  - a new authoritative smoke workflow surface: `.github/workflows/devcontainer-authoritative-smoke.yml`
- What is still missing is a clean CI/CD path that can:
  - build the image graph on GitHub-hosted Linux `x64`
  - optionally publish build outputs to GHCR
  - keep hosted build concerns separate from authoritative runtime acceptance

## Non-Goals

- No new Dockerfiles.
- No runtime-vs-builder split.
- No prebuilt toolchain base-image architecture in this phase.
- No change to Apple Silicon policy.
- No claim that GitHub-hosted runners replace the current authoritative `latest-kernel` proof surface.
- No replacement of `install.sh`, `chezmoi`, or `mise` bootstrap ownership.

## Assumptions

### Repository Visibility

- Preferred path: repository is public, so GitHub-hosted standard Linux runners can be used without paid runner minutes.
- If the repository is private, the same workflow design can still work, but total build cost and minute consumption must be treated as constrained and potentially unacceptable.

### Registry

- Publish target is GHCR under the current image naming model already encoded in `docker-bake.hcl`.
- Image publication remains optional in early rollout and should be separately gated by branch/ref policy.

### Runtime Acceptance

- Hosted `ubuntu-latest` is useful for build and early smoke.
- Hosted `ubuntu-latest` is not automatically equivalent to the repo's current self-hosted `latest-kernel` authoritative gate.
- Final acceptance for kernel-sensitive or policy-sensitive proof remains on the existing self-hosted Linux `amd64` surface unless explicitly changed later.

## Current Repo Contracts To Preserve

### Dockerfile Contract

Keep the root `Dockerfile` as the only build graph owner for:

- `base`
- `clang`
- `gcc`
- `final`
- `devcontainer`

Do not:

- rename stages
- reorder stages
- add a second primary Dockerfile
- move repo bootstrap out of `final`

### Devcontainer Contract

Preserve `.devcontainer/devcontainer.json` behavior:

- `linux/amd64`
- stable SSH socket path `/tmp/cpp-playground-ssh-agent.sock`
- thin host-user overlay flow via `.devcontainer/initialize-host.sh`

### Bootstrap Contract

Preserve the current bootstrap ownership:

- `install.sh` remains the checked-in bootstrap entrypoint inside `final`
- `chezmoi` remains host/bootstrap-state oriented
- `mise` remains the repo-managed CLI/tool pin layer

This means a future published image may still be based on the current `Dockerfile` outputs without changing the `chezmoi` or `mise` setup model.

## Proposed CI/CD Operating Model

## 1. Fast Hosted Integrity Gate

Keep `.github/workflows/tooling-validate.yml` as-is for:

- `uv run verify run`
- `pixi run ruff-check`
- `pixi run ty-check`

This remains the lowest-cost required gate.

## 2. Hosted Build Workflow

Add a new workflow that runs on GitHub-hosted Linux `x64`:

- runner: `ubuntu-latest`
- purpose: build the image graph and optionally publish to GHCR
- role: build/distribution lane, not authoritative runtime proof lane

Recommended workflow name:

- `devcontainer-build-hosted`

### Required Workflow Jobs

#### Job A: Contract Preflight

Run before any Docker build:

- `uv run verify run --suite image.stage-names.exact`
- `uv run verify run --suite image.bake-targets`
- `uv run verify run --suite devcontainer.from-final`
- `uv run verify run --suite build-optimization.pin-alignment`

Goal:

- fail fast if the repo contract drifted before consuming hosted Docker time

#### Job B: Hosted Build

Run on `ubuntu-latest` with Buildx:

Required steps:

1. checkout
2. setup Python
3. install repo tools (`mise`, `uv`, `pixi`) in the same pattern as existing workflows
4. `docker/setup-buildx-action`
5. `docker/login-action` for GHCR only when publish is enabled
6. build these Bake targets:
   - `base`
   - `clang`
   - `gcc`
   - `final`
   - `devcontainer`

Recommended commands:

```bash
docker buildx bake -f docker-bake.hcl base clang gcc final devcontainer
```

For non-publishing PR validation:

- use registry-backed cache import/export where possible
- avoid `--load` for the full graph unless a downstream smoke step requires it

For publishing refs:

- use `--push`
- publish only from approved refs such as:
  - `main`
  - version tags
  - explicit manual dispatch

#### Job C: Hosted Structural Smoke

If the hosted build also emits a `devcontainer` image reference accessible to the runner, run:

- `./scripts/smoke-devcontainer-image.sh`

Classification:

- this is a useful hosted smoke signal
- it is not a replacement for the self-hosted authoritative lane unless the repo policy changes later

#### Job D: Optional Artifact And Benchmark Export

For manual dispatch or tag builds only:

- run `./scripts/report-devcontainer-size.sh`
- optionally run `./scripts/benchmark-devcontainer-build.sh --scenario cold`

Store artifacts:

- benchmark JSON
- image size report
- top-layer summary

Do not make hosted benchmark artifacts mandatory for every PR in the first rollout.

## 3. Authoritative Runtime Gate

Keep `devcontainer-authoritative-smoke` on the current self-hosted runner class:

- `self-hosted`
- `Linux`
- `X64`
- `latest-kernel`

That workflow remains responsible for:

- `docker buildx bake -f docker-bake.hcl devcontainer --load`
- repo-owned smoke script execution
- repo-owned reflection/toolchain smoke inside the built image
- `uv run verify run`

## Publication Policy

## Refs That May Publish

- `main`
- release tags
- manual dispatch with explicit confirmation

Do not publish from ordinary pull requests.

## Tags

Keep publication aligned with `docker-bake.hcl` ownership.

Suggested tag set:

- branch tag for `main`
- immutable tag for git SHA
- optional release tag for semver refs

Do not invent a second tag ownership source outside Bake.

## Registry Cache Policy

Use GHCR-backed cache for hosted builds where helpful:

- import previous cache for repeat builds
- export cache only on trusted refs

Do not let cache policy become a second orchestration surface; keep it declared in workflow inputs and Bake usage only.

## Base Image Strategy

## Allowed In This Phase

- Continue using the current root `Dockerfile` as the only image-definition source.
- Publish the repo's own built images to GHCR.
- Continue running `install.sh` in `final`, which preserves current `chezmoi`/`mise`/bootstrap behavior.

## Explicitly Deferred

- consuming third-party experimental `clang-p2996` or GCC reflection images as canonical bases
- replacing the repo-built toolchain stages with externally managed base images
- moving bootstrap ownership away from `install.sh`
- publishing a permanent "toolchain base image" program as the primary flow

### Rationale

- Generic Ubuntu and LLVM images may exist, but they do not encode this repo's exact compiler refs, smoke expectations, or bootstrap contract.
- This repo's experimental compiler lanes are part of the product surface, not interchangeable dependencies.
- If prebuilt repo-owned base images are later desired, that should be a separate RFC layered on top of this CI/CD build surface.

## GitHub-Hosted Constraints To Design Around

- Hosted Linux runners have finite disk and runtime.
- The `clang` and `gcc` stages are the highest-risk steps for:
  - disk pressure
  - long wall time
  - cache misses

Therefore:

- do not require all heavyweight jobs on every PR in the first rollout
- prefer path filters and ref filters
- allow manual-dispatch publish runs
- keep authoritative acceptance on the self-hosted lane

## Rollout Plan

## Phase 1: Hosted Build, No Publish

Add `devcontainer-build-hosted` with:

- preflight contract checks
- hosted build of `devcontainer`
- optional hosted smoke

Do not publish yet.

Success criteria:

- workflow is green on `main`
- no repo contract drift
- hosted runner capacity is sufficient to complete builds reliably

## Phase 2: Trusted-Ref Publish

Enable GHCR publish from:

- `main`
- release tags
- manual dispatch

Success criteria:

- published tags are deterministic
- no accidental PR publishes
- GHCR permissions and provenance behavior are stable

## Phase 3: Optional Consumer Docs

Document:

- how to pull the published `devcontainer` image
- how published images relate to the repo's own devcontainer flow
- that hosted builds are a distribution surface, not a replacement for authoritative proof

## Proposed File Surface

The CI/CD implementation for this spec should stay small:

- add `.github/workflows/devcontainer-build-hosted.yml`
- optionally update `README.md`
- optionally update `verification/verification.toml` only if new contract assertions are strictly needed

Do not add:

- new Python modules
- new orchestration directories
- generated manifest files

## Validation

## Required Before Merge

- `uv run verify run`
- `pixi run ruff-check`
- `pixi run ty-check`
- hosted workflow YAML syntax and token validation

## Required Before Publish

- successful hosted build on trusted ref
- GHCR auth working
- output tags match Bake ownership

## Still Required For Authoritative Runtime Acceptance

- successful run of `devcontainer-authoritative-smoke` on self-hosted Linux `amd64`

## Acceptance Criteria

- CI/CD can build the repo images on GitHub-hosted Linux `x64`
- public-repo path can use free GitHub-hosted capacity
- the existing Dockerfile/stage/devcontainer contract is preserved
- publication, if enabled, is restricted to trusted refs
- no new control plane is introduced
- `install.sh` / `chezmoi` / `mise` ownership remains intact
- hosted build capability is clearly separated from authoritative runtime proof

## Open Questions

1. Is the repository intended to stay public, making GitHub-hosted builds effectively free?
2. Should hosted build success become a required PR check, or remain informational at first?
3. Should publish be enabled from `main` immediately, or only after a manual-dispatch soak period?
4. Does the team want a future RFC for repo-owned prebuilt base images after hosted CI/CD is stable?

## Next Step

If you want, I can turn this spec into the actual `.github/workflows/devcontainer-build-hosted.yml` next.
# Superseded

This archived spec is superseded by [docs/plans/2026-03-24-canonical-merged-plan.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plans/2026-03-24-canonical-merged-plan.md).
