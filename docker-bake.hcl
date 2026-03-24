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

variable "BASE_DISTRO" {
  default = "ubuntu"
}

variable "BASE_VERSION" {
  default = "25.10"
}

variable "DEBIAN_DISTRO" {
  default = "debian"
}

variable "DEBIAN_VERSION" {
  default = "13"
}

variable "APT_SNAPSHOT" {
  default = "20260322T000000Z"
}

variable "MISE_VERSION" {
  default = "2026.3.10"
}

variable "LLVM_VERSION" {
  default = "22.1.1"
}

variable "DEVCONTAINER_USERNAME" {
  default = "devcontainer"
}

target "_common" {
  context = "."
  dockerfile = "Dockerfile"
  platforms = ["${PLATFORM}"]
  args = {
    BASE_DISTRO = BASE_DISTRO
    BASE_VERSION = BASE_VERSION
    APT_SNAPSHOT = APT_SNAPSHOT
    MISE_VERSION = MISE_VERSION
    LLVM_VERSION = LLVM_VERSION
    DEVCONTAINER_USERNAME = DEVCONTAINER_USERNAME
  }
}

target "_common_debian" {
  inherits = ["_common"]
  args = {
    BASE_DISTRO = DEBIAN_DISTRO
    BASE_VERSION = DEBIAN_VERSION
    APT_SNAPSHOT = APT_SNAPSHOT
    MISE_VERSION = MISE_VERSION
    LLVM_VERSION = LLVM_VERSION
    DEVCONTAINER_USERNAME = DEVCONTAINER_USERNAME
  }
}

target "base" {
  inherits = ["_common"]
  target = "base"
  tags = ["${IMAGE}-base:${TAG}"]
}

target "clang" {
  inherits = ["_common"]
  target = "clang"
  tags = ["${IMAGE}-clang:${TAG}"]
}

target "gcc" {
  inherits = ["_common"]
  target = "gcc"
  tags = ["${IMAGE}-gcc:${TAG}"]
}

target "final" {
  inherits = ["_common"]
  target = "final"
  tags = ["${IMAGE}-final:${TAG}"]
}

target "devcontainer" {
  inherits = ["_common"]
  target = "devcontainer"
  pull = true
  tags = [
    "${REGISTRY}/${IMAGE}:${TAG}",
    "${IMAGE}:${TAG}",
  ]
  cache-from = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache",
  ]
  cache-to = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache,mode=max",
  ]
  attest = [
    "type=provenance,mode=min",
    "type=sbom",
  ]
}

target "devcontainer-load" {
  inherits = ["_common"]
  target = "devcontainer"
  pull = true
  tags = [
    "${REGISTRY}/${IMAGE}:${TAG}",
    "${IMAGE}:${TAG}",
  ]
  cache-from = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache",
  ]
  cache-to = [
    "type=registry,ref=${REGISTRY}/${IMAGE}:buildcache,mode=max",
  ]
  output = ["type=docker"]
}

target "devcontainer-debian" {
  inherits = ["_common_debian"]
  target = "devcontainer"
  tags = ["${IMAGE}:debian-${TAG}"]
}

group "default" {
  targets = ["devcontainer"]
}

group "toolchains" {
  targets = ["clang", "gcc"]
}

group "all" {
  targets = ["base", "clang", "gcc", "final", "devcontainer"]
}

group "debian" {
  targets = ["devcontainer-debian"]
}
