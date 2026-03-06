variable "IMAGE_TAG" {
  default = "dev"
}

variable "PLATFORM" {
  default = "linux/amd64"
}

group "default" {
  targets = ["clang_core", "gcc_core"]
}

target "clang_core" {
  context = "."
  dockerfile = "Dockerfile.clang-p2996"
  platforms = ["${PLATFORM}"]
  tags = ["cpp26-dev-clang:${IMAGE_TAG}"]
}

target "gcc_core" {
  context = "."
  dockerfile = "Dockerfile.gcc-reflection"
  platforms = ["${PLATFORM}"]
  tags = ["cpp26-dev-gcc:${IMAGE_TAG}"]
}

target "clang_quantlib" {
  context = "."
  dockerfile = "Dockerfile.clang-p2996-quantlib"
  platforms = ["${PLATFORM}"]
  tags = ["cpp26-dev-clang-quantlib:${IMAGE_TAG}"]
}
