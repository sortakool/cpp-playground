#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_DIR="${REPO_ROOT}/tooling/cpp26-dev-images"
MANIFEST_PATH="${REPO_ROOT}/tooling/tool-version-manifest.json"

TOOLCHAIN="all"
FLAVOR="core"
PLATFORM="$(python3 - <<'PY' "${MANIFEST_PATH}"
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
print(manifest["cpp26_dev_images"]["platform_default"])
PY
)"
IMAGE_TAG="$(python3 - <<'PY' "${MANIFEST_PATH}"
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
print(manifest["images"]["cpp26_dev_clang"]["default_tag"])
PY
)"
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
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
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

prefix() {
  local name="$1"
  if [[ -n "${REGISTRY_PREFIX}" ]]; then
    echo "${REGISTRY_PREFIX}/${name}"
  else
    echo "${name}"
  fi
}

repo_value() {
  local key="$1"
  python3 - <<'PY' "${MANIFEST_PATH}" "${key}"
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
print(manifest["images"][sys.argv[2]]["repository"])
PY
}

build_clang_core() {
  local image
  image="$(prefix "$(repo_value cpp26_dev_clang)"):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${IMAGE_DIR}/Dockerfile.clang-p2996" \
    -t "${image}" "${IMAGE_DIR}"
}

build_gcc_core() {
  local image
  image="$(prefix "$(repo_value cpp26_dev_gcc)"):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${IMAGE_DIR}/Dockerfile.gcc-reflection" \
    -t "${image}" "${IMAGE_DIR}"
}

build_clang_quantlib() {
  local base_image
  local image
  base_image="$(prefix "$(repo_value cpp26_dev_clang)"):${IMAGE_TAG}"
  image="$(prefix "$(repo_value cpp26_dev_clang_quantlib)"):${IMAGE_TAG}"
  echo "Building ${image}"
  run docker buildx build --platform "${PLATFORM}" --load \
    -f "${IMAGE_DIR}/Dockerfile.clang-p2996-quantlib" \
    --build-arg BASE_IMAGE="${base_image}" \
    -t "${image}" "${IMAGE_DIR}"
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
