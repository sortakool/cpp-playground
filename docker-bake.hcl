variable "REGISTRY" {
  default = "ghcr.io/ray-manaloto"
}

variable "IMAGE" {
  default = "cpp-devcontainer"
}

variable "TAG" {
  default = "dev"
}

variable "PLATFORM" {
  default = "linux/amd64"
}

variable "CPP26_IMAGE_TAG" {
  default = "dev"
}

variable "CPP26_REGISTRY_PREFIX" {
  default = ""
}

variable "REPO_BASE_IMAGE" {
  default = "cpp-devcontainer-repo-base"
}

variable "FINAL_BASE_IMAGE" {
  default = "cpp-devcontainer-base"
}

variable "CLANG_IMAGE" {
  default = "cpp26-dev-clang"
}

variable "GCC_IMAGE" {
  default = "cpp26-dev-gcc"
}

variable "CLANG_QUANTLIB_IMAGE" {
  default = "cpp26-dev-clang-quantlib"
}

variable "REPO_BASE_IMAGE_REF" {
  default = "${CPP26_REGISTRY_PREFIX}${REPO_BASE_IMAGE}:${CPP26_IMAGE_TAG}"
}

variable "FINAL_BASE_IMAGE_REF" {
  default = "${CPP26_REGISTRY_PREFIX}${FINAL_BASE_IMAGE}:${CPP26_IMAGE_TAG}"
}

variable "NODE_VERSION" {
  default = "25.8.1"
}

variable "NODE_MAJOR" {
  default = "25"
}

variable "MISE_VERSION" {
  default = "v2026.3.10"
}

variable "UV_VERSION" {
  default = "0.10.12"
}

variable "PIXI_VERSION" {
  default = "v0.66.0"
}

variable "LLVM_VERSION" {
  default = "22.1.1"
}

variable "DEVCONTAINER_USERNAME" {
  default = "devcontainer"
}

group "default" {
  targets = ["dev"]
}

group "cpp26_core" {
  targets = ["repo_base", "cpp26_clang_core", "cpp26_gcc_core", "final_base"]
}

group "cpp26_all" {
  targets = ["repo_base", "cpp26_clang_core", "cpp26_gcc_core", "final_base", "cpp26_clang_quantlib"]
}

target "cpp26_clang_core" {
  context = "tooling/cpp26-dev-images"
  dockerfile = "Dockerfile.clang-p2996"
  contexts = {
    base = "target:repo_base"
  }
  target = "artifact"
  platforms = ["${PLATFORM}"]
  args = {
    BASE_IMAGE = "base"
  }
  tags = ["${CPP26_REGISTRY_PREFIX}${CLANG_IMAGE}:${CPP26_IMAGE_TAG}"]
}

target "cpp26_gcc_core" {
  context = "tooling/cpp26-dev-images"
  dockerfile = "Dockerfile.gcc-reflection"
  contexts = {
    base = "target:repo_base"
  }
  target = "artifact"
  platforms = ["${PLATFORM}"]
  args = {
    BASE_IMAGE = "base"
  }
  tags = ["${CPP26_REGISTRY_PREFIX}${GCC_IMAGE}:${CPP26_IMAGE_TAG}"]
}

target "repo_base" {
  context = "."
  dockerfile = ".devcontainer/Dockerfile"
  target = "repo_base"
  platforms = ["${PLATFORM}"]
  tags = ["${REPO_BASE_IMAGE_REF}"]
  args = {
    NODE_VERSION = NODE_VERSION
    NODE_MAJOR = NODE_MAJOR
    MISE_VERSION = MISE_VERSION
    UV_VERSION = UV_VERSION
    PIXI_VERSION = PIXI_VERSION
    LLVM_VERSION = LLVM_VERSION
    UBUNTU_VERSION = "24.04"
  }
}

target "final_base" {
  context = "."
  dockerfile = ".devcontainer/Dockerfile"
  target = "final_base"
  contexts = {
    repo_base = "target:repo_base"
    clang_core = "target:cpp26_clang_core"
    gcc_core = "target:cpp26_gcc_core"
  }
  platforms = ["${PLATFORM}"]
  tags = ["${FINAL_BASE_IMAGE_REF}"]
  args = {
    REPO_BASE_IMAGE = "repo_base"
    CLANG_IMAGE = "clang_core"
    GCC_IMAGE = "gcc_core"
    LLVM_VERSION = LLVM_VERSION
  }
}

target "cpp26_clang_quantlib" {
  context = "tooling/cpp26-dev-images"
  dockerfile = "Dockerfile.clang-p2996-quantlib"
  contexts = {
    base = "target:repo_base"
    clang_core = "target:cpp26_clang_core"
  }
  platforms = ["${PLATFORM}"]
  args = {
    BASE_IMAGE = "base"
    CLANG_IMAGE = "clang_core"
  }
  tags = ["${CPP26_REGISTRY_PREFIX}${CLANG_QUANTLIB_IMAGE}:${CPP26_IMAGE_TAG}"]
}

target "dev" {
  context = "."
  dockerfile = ".devcontainer/Dockerfile"
  target = "devcontainer"
  contexts = {
    final_base = "target:final_base"
  }
  platforms = ["${PLATFORM}"]
  pull = true

  tags = [
    "${IMAGE}:${TAG}",
    "${REGISTRY}/${IMAGE}:${TAG}"
  ]

  cache-from = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache"
  ]

  cache-to = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache,mode=max"
  ]

  attest = [
    "type=provenance,mode=min",
    "type=sbom"
  ]

  args = {
    FINAL_BASE_IMAGE = "final_base"
    DEVCONTAINER_USERNAME = DEVCONTAINER_USERNAME
  }
}
