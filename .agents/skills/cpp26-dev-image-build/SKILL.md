---
name: cpp26-dev-image-build
description: Build and update pinned Ubuntu x86_64 C++26 reflection Docker images (clang-p2996 primary, GCC reflection optional) with Conan, vcpkg, sanitizers, and debugging tools. Use when creating or refreshing reflection-ready C++ toolchain images or preparing environments for mirror_bridge, merton-market-maker, and simdjson/p2996.
---

# C++26 Dev Image Build

Build and refresh pinned C++26 reflection development images targeting `linux/amd64`.

## Use This Skill For

- Build fresh reflection-enabled toolchain images.
- Refresh pinned compiler refs in `references/toolchain-lock.yaml`.
- Build sample-project flavor images (QuantLib variant).

## Inputs

- Toolchain: `clang`, `gcc`, or `all`.
- Flavor: `core` or `quantlib`.
- Optional registry prefix and tag.

## Workflow

1. Read `tooling/tool-version-manifest.json` and keep the `cpp26_dev_images` pins authoritative.
2. Build toolchain stages via Bake from root `Dockerfile`.
3. Keep clang/gcc stage builds parallel from `base`.
4. Delegate runtime verification to `$cpp26-dev-image-validate`.
5. Delegate publishing/sync to `$cpp26-dev-image-publish`.

## Commands

```bash
# Inspect image targets
docker buildx bake -f docker-bake.hcl --list=targets

# Build compiler lanes in parallel
docker buildx bake -f docker-bake.hcl clang gcc

# Build final and devcontainer surfaces
docker buildx bake -f docker-bake.hcl final devcontainer
```

## Outputs

- Local Docker images tagged with selected toolchain/flavor/tag.
- Updated toolchain lock file when bumping refs.
