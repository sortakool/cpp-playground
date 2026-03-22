variable "IMAGE_TAG" {
  default = "dev"
}

variable "PLATFORM" {
  default = "linux/amd64"
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

variable "CLANG_BASE_IMAGE" {
  default = "cpp26-dev-clang:dev"
}

group "default" {
  targets = ["clang_core", "gcc_core"]
}

target "clang_core" {
  context = "."
  dockerfile = "Dockerfile.clang-p2996"
  platforms = ["${PLATFORM}"]
  tags = ["${CLANG_IMAGE}:${IMAGE_TAG}"]
}

target "gcc_core" {
  context = "."
  dockerfile = "Dockerfile.gcc-reflection"
  platforms = ["${PLATFORM}"]
  tags = ["${GCC_IMAGE}:${IMAGE_TAG}"]
}

target "clang_quantlib" {
  context = "."
  dockerfile = "Dockerfile.clang-p2996-quantlib"
  platforms = ["${PLATFORM}"]
  args = {
    BASE_IMAGE = CLANG_BASE_IMAGE
  }
  tags = ["${CLANG_QUANTLIB_IMAGE}:${IMAGE_TAG}"]
}
