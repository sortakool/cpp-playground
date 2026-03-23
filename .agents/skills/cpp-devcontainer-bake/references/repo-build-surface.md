# Repo Build Surface

## Root Bake File

`docker-bake.hcl` is the unified build surface for:

- `dev_base`
- `cpp26_clang_core`
- `cpp26_gcc_core`
- `cpp26_clang_quantlib`
- `dev`

Groups:

- `default` -> `dev`
- `cpp26_core` -> `cpp26_clang_core`, `cpp26_gcc_core`
- `cpp26_all` -> `cpp26_clang_core`, `cpp26_gcc_core`, `cpp26_clang_quantlib`

## Shared Base And Runtime Split

`.devcontainer/Dockerfile` exports two important stages:

- `base`
- `runtime`

`docker-bake.hcl` reflects that split:

- `dev_base` builds the `base` stage and tags it as `cpp-devcontainer-base:<CPP26_IMAGE_TAG>`
- `cpp26_clang_core` and `cpp26_gcc_core` both use `target:dev_base`
- `dev` points its `base`, `clang_core`, and `gcc_core` contexts at those staged targets and builds the `runtime` stage

The repo validation code explicitly checks that this graph exists.

## Devcontainer Targets

`dev_base`:

- `context = "."`
- `dockerfile = ".devcontainer/Dockerfile"`
- `target = "base"`
- tags:
  - `cpp-devcontainer-base:<CPP26_IMAGE_TAG>`
- platforms:
  - `linux/amd64`

`dev`:

- `context = "."`
- `dockerfile = ".devcontainer/Dockerfile"`
- `target = "runtime"`
- `platforms = ["linux/amd64"]`
- `pull = true`
- tags:
  - `cpp-devcontainer:<TAG>`
  - `ghcr.io/ray-manaloto/cpp-devcontainer:<TAG>`
- registry cache configured on the target:
  - `cache-from = type=registry,ref=ghcr.io/ray-manaloto/cpp-devcontainer:buildcache`
  - `cache-to = type=registry,ref=ghcr.io/ray-manaloto/cpp-devcontainer:buildcache,mode=max`
- attestations:
  - `type=provenance,mode=min`
  - `type=sbom`

Build args passed from Bake:

- `CLANG_BASE_IMAGE`
- `GCC_BASE_IMAGE`
- `NODE_VERSION`
- `NODE_MAJOR`
- `MISE_VERSION`
- `UV_VERSION`
- `PIXI_VERSION`
- `LLVM_VERSION`
- `DEVCONTAINER_USERNAME`
- `UBUNTU_VERSION`

## Base Image Relationship

The runtime stage consumes three incoming image references:

- `BASE_IMAGE`
- `CLANG_BASE_IMAGE`
- `GCC_BASE_IMAGE`

In the checked-in Dockerfile these are named:

- `BASE_IMAGE`
- `CLANG_IMAGE`
- `GCC_IMAGE`

For local builds the control plane resolves them to local tags:

- `cpp-devcontainer-base:<tag>`
- `cpp26-dev-clang:<tag>`
- `cpp26-dev-gcc:<tag>`

That is the important project-specific detail: the host build path materializes those images first, then feeds the final wrapper build with explicit local tags.

## Control Plane Behavior

`python3 -m tooling build-devcontainer-image --image-tag <tag>` is not a thin alias. It:

1. Reads the repo manifest and platform default.
2. Resolves `DEVCONTAINER_USERNAME` from the host short username and validates it is not root.
3. Builds these Bake targets locally, one at a time:
   - `dev_base`
   - `cpp26_clang_core`
   - `cpp26_gcc_core`
4. For each of those staged targets, forces:
   - `output=type=docker`
   - `cache-from=`
   - `cache-to=`
5. Runs a final `docker buildx build --load -f .devcontainer/Dockerfile` with:
   - `PLATFORM=linux/amd64`
   - `BASE_IMAGE=cpp-devcontainer-base:<tag>`
   - `CLANG_IMAGE=cpp26-dev-clang:<tag>`
   - `GCC_IMAGE=cpp26-dev-gcc:<tag>`
   - `DEVCONTAINER_USERNAME=<host short username>`

This means the local build path is explicitly staged. Do not describe it as "run Bake target `dev`" unless you are talking about graph inspection or intentionally changing the build system.

## Why The Skill Should Not Default To `docker buildx bake dev`

Inference from the current checked-in code:

- the Bake file defines the complete graph
- the control plane chooses a host-aware staged local-materialization flow
- host username parity and local image loading are first-class concerns

For this repo, the safe advice is:

- inspect the graph with Bake
- build locally with `python3 -m tooling build-devcontainer-image`

## Verified Inspection Commands

These commands parsed successfully against the current repo state:

```bash
docker buildx bake -f docker-bake.hcl --list=targets
docker buildx bake -f docker-bake.hcl --print dev_base
docker buildx bake -f docker-bake.hcl --print dev
python3 -m tooling print-devcontainer-env cpp-devcontainer:dev
```

Use them as the first debugging layer before changing the build definition.
