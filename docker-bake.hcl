variable "REGISTRY" {
  default = "ghcr.io/ray-manaloto"
}

variable "IMAGE" {
  default = "cpp-devcontainer"
}

variable "TAG" {
  default = "dev"
}

variable "CLANG_BASE_IMAGE" {
  default = "cpp26-dev-clang:dev"
}

variable "GCC_BASE_IMAGE" {
  default = "cpp26-dev-gcc:dev"
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

group "default" {
  targets = ["dev"]
}

target "dev" {
  context = "."
  dockerfile = ".devcontainer/Dockerfile"
  platforms = ["linux/amd64"]
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
    CLANG_BASE_IMAGE = CLANG_BASE_IMAGE
    GCC_BASE_IMAGE = GCC_BASE_IMAGE
    NODE_VERSION = NODE_VERSION
    NODE_MAJOR = NODE_MAJOR
    MISE_VERSION = MISE_VERSION
    UV_VERSION = UV_VERSION
    PIXI_VERSION = PIXI_VERSION
    LLVM_VERSION = LLVM_VERSION
  }
}
