#include "test_support.hpp"

#include <fcntl.h>
#include <linux/memfd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <cstdint>
#include <string>

namespace {

int memfd_create_compat(const char* name, unsigned int flags) {
  return static_cast<int>(syscall(SYS_memfd_create, name, flags));
}

}  // namespace

int main() {
  constexpr std::size_t kBytes = 4096;
  const auto memfd_start = kernel_test::clock::now();
  const int memfd = memfd_create_compat("cpp-playground-shm", MFD_CLOEXEC);
  if (memfd < 0) {
    return kernel_test::fail("memfd_create");
  }
  if (ftruncate(memfd, static_cast<off_t>(kBytes)) != 0) {
    close(memfd);
    return kernel_test::fail("memfd_ftruncate");
  }

  auto* memfd_writer = static_cast<std::uint64_t*>(
      mmap(nullptr, kBytes, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, 0));
  if (memfd_writer == MAP_FAILED) {
    close(memfd);
    return kernel_test::fail("memfd_mmap_writer");
  }
  auto* memfd_reader = static_cast<std::uint64_t*>(
      mmap(nullptr, kBytes, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, 0));
  if (memfd_reader == MAP_FAILED) {
    munmap(memfd_writer, kBytes);
    close(memfd);
    return kernel_test::fail("memfd_mmap_reader");
  }

  memfd_writer[0] = 0xC0FFEE1234567890ULL;
  kernel_test::metric("memfd_create_us", kernel_test::micros_since(memfd_start));
  kernel_test::metric("memfd_visible_value", memfd_reader[0]);

  const std::string shm_name = "/cpp-playground-" + std::to_string(getpid());
  const auto shm_start = kernel_test::clock::now();
  const int shm_fd = shm_open(shm_name.c_str(), O_CREAT | O_RDWR | O_EXCL, 0600);
  if (shm_fd < 0) {
    munmap(memfd_reader, kBytes);
    munmap(memfd_writer, kBytes);
    close(memfd);
    return kernel_test::fail("shm_open");
  }
  if (ftruncate(shm_fd, static_cast<off_t>(kBytes)) != 0) {
    shm_unlink(shm_name.c_str());
    close(shm_fd);
    munmap(memfd_reader, kBytes);
    munmap(memfd_writer, kBytes);
    close(memfd);
    return kernel_test::fail("shm_ftruncate");
  }

  auto* shm_writer = static_cast<std::uint64_t*>(
      mmap(nullptr, kBytes, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0));
  if (shm_writer == MAP_FAILED) {
    shm_unlink(shm_name.c_str());
    close(shm_fd);
    munmap(memfd_reader, kBytes);
    munmap(memfd_writer, kBytes);
    close(memfd);
    return kernel_test::fail("shm_mmap_writer");
  }
  auto* shm_reader = static_cast<std::uint64_t*>(
      mmap(nullptr, kBytes, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0));
  if (shm_reader == MAP_FAILED) {
    munmap(shm_writer, kBytes);
    shm_unlink(shm_name.c_str());
    close(shm_fd);
    munmap(memfd_reader, kBytes);
    munmap(memfd_writer, kBytes);
    close(memfd);
    return kernel_test::fail("shm_mmap_reader");
  }

  shm_writer[0] = 0xABCD1234ULL;
  kernel_test::metric("shm_open_us", kernel_test::micros_since(shm_start));
  kernel_test::metric("shm_visible_value", shm_reader[0]);

  const bool ok = memfd_reader[0] == 0xC0FFEE1234567890ULL && shm_reader[0] == 0xABCD1234ULL;

  munmap(shm_reader, kBytes);
  munmap(shm_writer, kBytes);
  shm_unlink(shm_name.c_str());
  close(shm_fd);
  munmap(memfd_reader, kBytes);
  munmap(memfd_writer, kBytes);
  close(memfd);

  if (!ok) {
    return kernel_test::fail_message("shared_visibility", "shared mappings did not observe writes");
  }
  return kernel_test::pass("shared_memory_smoke");
}
