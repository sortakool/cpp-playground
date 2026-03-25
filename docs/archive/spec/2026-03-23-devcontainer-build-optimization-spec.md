# Devcontainer Build Optimization Spec

## Summary

- Goal: improve root Dockerfile and devcontainer build speed and image size without violating the repo's current build, verification, and runtime contracts.
- This spec replaces the earlier broad optimization program with an execution-ready, lower-risk plan grounded in the current repo surface.
- The first phase stays inside the existing architecture:
  - one root `Dockerfile`
  - one thin `.devcontainer/Dockerfile.host-user` overlay
  - exact stage set: `base`, `clang`, `gcc`, `final`, `devcontainer`
  - Linux `amd64` as the only authoritative proof surface
- The first phase does **not** add a standalone toolchain manifest, does **not** split runtime from builder, and does **not** introduce a second orchestration/control plane.

## Why This Exists

The repo already has a narrowed build contract:

- [README.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md) defines one root `Dockerfile` plus `docker buildx bake` as the build surface.
- [verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml) enforces the Dockerfile set, stage names, Bake targets, and thin-devcontainer model.
- [pixi.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml) exposes only leaf checks and `verify run`; it does not expose a benchmark harness, drift monitor, or image optimization control plane.
- [tooling-validate.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/tooling-validate.yml) is currently the only hosted verification workflow, and it does not prove the devcontainer image on authoritative Linux `amd64`.

The previous optimization plan was directionally useful but too broad. It mixed architectural changes, benchmark design, CI changes, and new skill/control-plane pieces before the repo had a stable measurement and gating surface.

## Hard Constraints

- Preserve the current Dockerfile contract enforced by [verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml):
  - one root `Dockerfile`
  - `.devcontainer/Dockerfile.host-user` as the only additional Dockerfile
  - exact stage order `base`, `clang`, `gcc`, `final`, `devcontainer`
  - `devcontainer` derives directly from `final`
  - repo bootstrap remains in `final`
- Preserve the current devcontainer runtime contract in [.devcontainer/devcontainer.json](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/devcontainer.json):
  - Linux `amd64`
  - stable in-container SSH socket path `/tmp/cpp-playground-ssh-agent.sock`
  - thin host-user overlay flow via [.devcontainer/initialize-host.sh](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/initialize-host.sh)
- Preserve the Apple Silicon caveat and do not treat emulated `linux/amd64` on Apple Silicon as authoritative proof.
- Do not add new Python console scripts or reintroduce a broad Python orchestration layer. New automation in this program should live in `scripts/`, `benchmarks/`, `verification/`, `pixi.toml`, and GitHub Actions.
- Any change that breaks the current Dockerfile/stage/devcontainer contract requires a separate RFC and must not be smuggled in as an optimization patch.

## Non-Goals For V1

- No standalone toolchain manifest file.
- No runtime-vs-builder image split.
- No prebuilt toolchain base-image publication strategy.
- No attempt to optimize or standardize macOS/Apple Silicon as an authoritative proof surface.
- No automated merge or auto-update bot for compiler/base-image bumps.
- No benchmark of "devcontainer create-to-ready" until a reproducible non-interactive harness exists.
- No generalized multi-agent research framework changes in the repo as part of this effort.

## Source-Of-Truth Model

The repo needs one explicit ownership model, not a new abstraction layer.

### Owner: `Dockerfile`

The root [Dockerfile](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/Dockerfile) owns:

- stage graph and stage-local behavior
- compiler source repositories and pinned refs
- stage-local smoke commands
- which artifacts are copied into `final`
- which runtime packages are installed in `devcontainer`

### Owner: `docker-bake.hcl`

[docker-bake.hcl](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docker-bake.hcl) owns:

- build interface and target/group surface
- published tags
- platform selection
- cache configuration
- attest/SBOM settings
- operator-facing values for `BASE_DISTRO`, `BASE_VERSION`, `APT_SNAPSHOT`, `MISE_VERSION`, `LLVM_VERSION`, and `DEVCONTAINER_USERNAME`

### Owner: `verification/verification.toml`

[verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml) owns:

- contract assertions for the Dockerfile set
- stage/order invariants
- Bake target invariants
- thin-devcontainer assertions
- documentation/build-surface consistency checks

### Explicit V1 Decision

- Do **not** add a new toolchain manifest in V1.
- Instead, add verification that the operator-facing build args in `docker-bake.hcl` and the fallback defaults in `Dockerfile` stay aligned where duplication is unavoidable.
- If a future single-file generator is desired, that must come through a separate RFC after the benchmark and gating surface is stable.

## CI Operating Model

### Required Hosted Gate

Keep [tooling-validate.yml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.github/workflows/tooling-validate.yml) as a required fast gate for:

- `uv run verify run`
- `pixi run ruff-check`
- `pixi run ty-check`

This remains the low-cost integrity gate.

### Required Authoritative Gate

Add a new required workflow for PRs that touch any of:

- `Dockerfile`
- `docker-bake.hcl`
- `.devcontainer/**`
- `verification/**`
- `install.sh`
- `.github/workflows/**`

#### Runner

Use the existing self-hosted Linux `amd64` surface first:

- `self-hosted`
- `Linux`
- `X64`
- `latest-kernel`

If that runner is unavailable, the PR stays blocked in V1. There is no hosted fallback for authoritative proof in this phase.

#### New Gate Name

`devcontainer-authoritative-smoke`

#### Required Checks In That Workflow

1. `docker buildx bake -f docker-bake.hcl devcontainer --load`
2. repo-owned image smoke script for the built `devcontainer` image
3. repo-owned reflection/toolchain smoke inside the built image
4. `uv run verify run`

This workflow must use exact repo-owned scripts for image/toolchain smoke rather than ad-hoc shell snippets embedded only in CI.

## Benchmark Model

V1 only measures metrics that can be reproduced from the current repo surface.

### Metrics To Measure In V1

- cold `devcontainer` build wall time
- warm rebuild wall time after a repo-only source change
- warm rebuild wall time after a `.devcontainer`-only change
- local uncompressed image size
- exported compressed image size
- top image layers by size
- filesystem footprint for:
  - `/opt/llvm`
  - `/opt/clang-p2996`
  - `/opt/gcc-reflection`
  - `/opt/cpp-playground`

### Metrics Deferred Out Of V1

- cache reuse ratio proxy
- devcontainer create-to-ready time
- CI minutes estimate
- toolchain update lead time

These are deferred because the repo does not yet have a reproducible harness for them.

### Benchmark Artifact Schema

Create a repo-owned schema under `benchmarks/devcontainer/` with these required fields:

- `schema_version`
- `run_id`
- `git_sha`
- `git_dirty`
- `runner_name`
- `runner_labels`
- `docker_version`
- `buildx_version`
- `scenario`
- `platform`
- `image_ref`
- `timings_s`
- `image_size_bytes`
- `compressed_size_bytes`
- `top_layers`
- `filesystem_sizes`
- `result`

### Decision Rules

- Performance changes:
  - use 3 paired runs on the same runner class
  - compare medians
  - accept only if improvement is at least `10%` or `300s`
  - reject if any protected secondary metric regresses by more than `5%`
- Size changes:
  - accept only if size improves by at least `5%`
  - reject if build time regresses by more than `5%`
- If run metadata differs across comparisons, the comparison is invalid.
- If run spread is high enough that the median is not stable, rerun once; if still unstable, discard the experiment.

## Planned File Surface

The first implementation wave should add only a small, concrete surface:

- Create `scripts/smoke-devcontainer-image.sh`
- Create `scripts/benchmark-devcontainer-build.sh`
- Create `scripts/report-devcontainer-size.sh`
- Create `benchmarks/devcontainer/schema.json`
- Create `benchmarks/devcontainer/README.md`
- Add benchmark and smoke leaf tasks in [pixi.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/pixi.toml)
- Add `devcontainer-authoritative-smoke` workflow
- Add schema/pin-alignment verification in [verification/verification.toml](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/verification/verification.toml)
- Update [README.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/README.md) with the new benchmark/smoke command surface

Do not add a new Python package module or a new repo-wide orchestration directory.

## Optimization Backlog Allowed In V1

Only these hypothesis families are in scope for the first optimization wave:

1. `COPY` invalidation boundary reduction for repo bootstrap in `final`
2. package and layer cleanup in `base` and `devcontainer`
3. cache-friendly adjustments that do not change the stage graph
4. artifact stripping or pruning that preserves toolchain usability and smoke coverage
5. reduced repo copy surface through `.dockerignore` or equivalent build-context hygiene

## Backlog Explicitly Out Of Scope In V1

These ideas are deferred because they conflict with current repo contracts or materially expand the control plane:

- new Dockerfiles
- new permanent stage topology
- runtime-vs-builder split
- prebuilt toolchain base images as the primary flow
- generated manifest control plane
- benchmark-driven merge policy before authoritative smoke exists

## User-Provisioning Parity Requirement

The repo currently carries similar user-provisioning logic in:

- [Dockerfile](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/Dockerfile)
- [.devcontainer/Dockerfile.host-user](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.devcontainer/Dockerfile.host-user)

V1 must add one of:

- shared provisioning logic reused by both surfaces, or
- a dedicated parity verification suite that proves both surfaces still agree on username/home/sudo/SSH assumptions

This is a release blocker for optimization changes that touch user/runtime setup.

## Implementation Phases

### Phase 0: Establish Proof

Deliverables:

- required `devcontainer-authoritative-smoke` workflow
- repo-owned image/toolchain smoke scripts
- verification for pin alignment and benchmark schema presence

Exit criteria:

- hosted `repo-verify` still passes
- authoritative Linux `amd64` smoke exists and is required

### Phase 1: Establish Measurement

Deliverables:

- benchmark schema
- benchmark scripts
- `pixi` leaf tasks for smoke and benchmark entry points
- first baseline benchmark artifact from the authoritative runner class

Exit criteria:

- baseline artifact can be reproduced
- comparisons are stable enough for paired-run decisions

### Phase 2: Constrained Optimization

Deliverables:

- one hypothesis at a time
- before/after benchmark artifact for each accepted change
- update to docs and verification where needed

Exit criteria:

- at least one accepted improvement lands without violating contracts

### Phase 3: Update Monitoring

Deliverables:

- scheduled/manual drift-report workflow for base image and compiler refs
- documented bump procedure that always routes through authoritative smoke

Exit criteria:

- upstream drift is observable without auto-merging changes

## Acceptance Criteria

This program is successful when all of the following are true:

- the repo has one required authoritative Linux `amd64` devcontainer/toolchain smoke gate
- benchmark artifacts are schema-validated and reproducible
- build pin ownership is explicit and verified
- at least one optimization is merged with measured evidence
- no change weakens the current Dockerfile/devcontainer contract without a separate RFC
- the SSH and host-user runtime contract remains intact on the checked-in macOS path

## Validation Commands After Implementation

The intended validation surface after the first implementation wave is:

```bash
uv run verify run
pixi run docker-bake-check
pixi run dockerfile-lint
pixi run ruff-check
pixi run ty-check
pixi run smoke-devcontainer-image
pixi run benchmark-devcontainer-cold
pixi run benchmark-devcontainer-warm-repo-change
pixi run benchmark-devcontainer-warm-devcontainer-change
```

## Notes

- Multi-agent or adversarial reviewers may support research and review, but they are not the source of truth. The source of truth remains the active spec plus current repo files.
- Any future proposal to introduce a standalone manifest, prebuilt toolchain base image, or different Dockerfile topology must be written as a separate RFC after this program proves the narrow path first.
# Superseded

This archived spec is superseded by [docs/plans/2026-03-24-canonical-merged-plan.md](/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/docs/plans/2026-03-24-canonical-merged-plan.md).
