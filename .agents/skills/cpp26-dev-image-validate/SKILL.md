---
name: cpp26-dev-image-validate
description: Validate C++26 clang/gcc dev images with reflection and sanitizer smoke tests. Use when asked to verify image health, reflection flag support, or sanitizer readiness before publishing or project use.
---

# C++26 Dev Image Validate

Use this skill for runtime validation only.

## Workflow

1. Run `scripts/test_images.sh`.
2. Choose `--toolchain clang|gcc|all`.
3. Optionally set `--flavor core|quantlib` (quantlib applies to clang only).
4. Optionally set `--registry-prefix` and `--image-tag`.
5. Run `--dry-run` first when checking command composition.
6. Report failing image refs and failing check names.

## Commands

```bash
./scripts/test_images.sh --toolchain all --image-tag dev
./scripts/test_images.sh --toolchain clang --flavor quantlib --image-tag dev
./scripts/test_images.sh --toolchain gcc --registry-prefix ghcr.io/ray-manaloto --image-tag 2026.03.05
./scripts/test_images.sh --toolchain all --dry-run
```
