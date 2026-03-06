#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ASSETS_DIR="${SKILL_DIR}/assets"
LOCK_FILE="${SKILL_DIR}/references/toolchain-lock.yaml"

TOOLCHAIN="all"
FLAVOR="core"
PLATFORM="linux/amd64"
IMAGE_TAG="dev"
REGISTRY_PREFIX=""
DRY_RUN=0

usage() {
  cat <<USAGE
Usage: $0 [options]
  --toolchain clang|gcc|all
  --flavor core|quantlib
  --platform linux/amd64
  --image-tag TAG
  --registry-prefix PREFIX
  --dry-run
USAGE
}

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --toolchain) TOOLCHAIN="$2"; shift 2 ;;
    --flavor) FLAVOR="$2"; shift 2 ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    --image-tag) IMAGE_TAG="$2"; shift 2 ;;
    --registry-prefix) REGISTRY_PREFIX="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ "${TOOLCHAIN}" != "clang" && "${TOOLCHAIN}" != "gcc" && "${TOOLCHAIN}" != "all" ]]; then
  echo "Invalid toolchain: ${TOOLCHAIN}" >&2
  exit 1
fi

if [[ "${FLAVOR}" != "core" && "${FLAVOR}" != "quantlib" ]]; then
  echo "Invalid flavor: ${FLAVOR}" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

clang_ref="$(grep '^clang_ref:' "${LOCK_FILE}" | awk '{print $2}' | tr -d '"')"
gcc_ref="$(grep '^gcc_ref:' "${LOCK_FILE}" | awk '{print $2}' | tr -d '"')"
ubuntu_version="$(grep '^ubuntu_version:' "${LOCK_FILE}" | awk '{print $2}' | tr -d '"')"
vcpkg_ref="$(grep '^vcpkg_ref:' "${LOCK_FILE}" | awk '{print $2}' | tr -d '"')"
quantlib_version="$(grep '^quantlib_version:' "${LOCK_FILE}" | awk '{print $2}' | tr -d '"')"

prefix() {
  local name="$1"
  if [[ -n "${REGISTRY_PREFIX}" ]]; then
    echo "${REGISTRY_PREFIX}/${name}"
  else
    echo "${name}"
  fi
}

build_clang_core() {
  local image
  image="$(prefix cpp26-dev-clang):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${ASSETS_DIR}/Dockerfile.clang-p2996" \
    --build-arg UBUNTU_VERSION="${ubuntu_version}" \
    --build-arg CLANG_P2996_REF="${clang_ref}" \
    --build-arg VCPKG_REF="${vcpkg_ref}" \
    -t "${image}" "${ASSETS_DIR}"
}

build_gcc_core() {
  local image
  image="$(prefix cpp26-dev-gcc):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${ASSETS_DIR}/Dockerfile.gcc-reflection" \
    --build-arg UBUNTU_VERSION="${ubuntu_version}" \
    --build-arg GCC_REFLECTION_REF="${gcc_ref}" \
    --build-arg VCPKG_REF="${vcpkg_ref}" \
    -t "${image}" "${ASSETS_DIR}"
}

build_clang_quantlib() {
  local base_image
  local image
  base_image="$(prefix cpp26-dev-clang):${IMAGE_TAG}"
  image="$(prefix cpp26-dev-clang-quantlib):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${ASSETS_DIR}/Dockerfile.clang-p2996-quantlib" \
    --build-arg BASE_IMAGE="${base_image}" \
    --build-arg QUANTLIB_VERSION="${quantlib_version}" \
    -t "${image}" "${ASSETS_DIR}"
}

if [[ "${TOOLCHAIN}" == "clang" || "${TOOLCHAIN}" == "all" ]]; then
  build_clang_core
  if [[ "${FLAVOR}" == "quantlib" ]]; then
    build_clang_quantlib
  fi
fi

if [[ "${TOOLCHAIN}" == "gcc" || "${TOOLCHAIN}" == "all" ]]; then
  if [[ "${FLAVOR}" == "quantlib" ]]; then
    echo "quantlib flavor is clang-only; building gcc core instead"
  fi
  build_gcc_core
fi

echo "Build workflow completed"
