---
name: cpp26-dev-image-build
description: Build and update pinned Ubuntu x86_64 C++26 reflection Docker images (clang-p2996 primary, GCC reflection optional) with Conan, vcpkg, sanitizers, and debugging tools. Use when creating or refreshing reflection-ready C++ toolchain images or preparing environments for mirror_bridge, merton-market-maker, and simdjson/p2996.
---

# C++26 Dev Image Build

Build and refresh pinned C++26 reflection development images targeting `linux/amd64` from macOS or Linux hosts.

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
2. Build image targets with `python3 -m tooling build-cpp26-images`.
3. Check upstream pin drift with `python3 -m tooling check-cpp26-toolchain-pins`.
4. Bump pins explicitly with `python3 -m tooling bump-cpp26-toolchain-pins`.
5. Delegate runtime verification to `$cpp26-dev-image-validate`.
6. Delegate publishing/sync to `$cpp26-dev-image-publish`.

## Commands

```bash
# Build all core images locally
python3 -m tooling build-cpp26-images --toolchain all --flavor core

# Build clang quantlib variant
python3 -m tooling build-cpp26-images --toolchain clang --flavor quantlib --image-tag dev

# Check if pins are stale
python3 -m tooling check-cpp26-toolchain-pins

# Update lock file pins to latest branch heads
python3 -m tooling bump-cpp26-toolchain-pins
```

## Outputs

- Local Docker images tagged with selected toolchain/flavor/tag.
- Updated toolchain lock file when bumping refs.
