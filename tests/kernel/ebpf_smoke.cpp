#include "test_support.hpp"

#include <linux/bpf.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <cstdint>
#include <cstring>

namespace {

int bpf_syscall(enum bpf_cmd cmd, union bpf_attr* attr) {
  return static_cast<int>(syscall(SYS_bpf, cmd, attr, sizeof(*attr)));
}

std::uint64_t ptr_to_u64(const void* ptr) {
  return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(ptr));
}

}  // namespace

int main() {
  union bpf_attr create_attr;
  std::memset(&create_attr, 0, sizeof(create_attr));
  create_attr.map_type = BPF_MAP_TYPE_ARRAY;
  create_attr.key_size = sizeof(std::uint32_t);
  create_attr.value_size = sizeof(std::uint64_t);
  create_attr.max_entries = 1;
  std::memcpy(create_attr.map_name, "cpp_playground", 14);

  const auto create_start = kernel_test::clock::now();
  const int map_fd = bpf_syscall(BPF_MAP_CREATE, &create_attr);
  if (map_fd < 0) {
    return kernel_test::fail("bpf_map_create");
  }

  std::uint32_t key = 0;
  std::uint64_t value = 0x123456789ULL;
  union bpf_attr update_attr;
  std::memset(&update_attr, 0, sizeof(update_attr));
  update_attr.map_fd = static_cast<std::uint32_t>(map_fd);
  update_attr.key = ptr_to_u64(&key);
  update_attr.value = ptr_to_u64(&value);
  update_attr.flags = BPF_ANY;
  if (bpf_syscall(BPF_MAP_UPDATE_ELEM, &update_attr) < 0) {
    close(map_fd);
    return kernel_test::fail("bpf_map_update");
  }

  std::uint64_t observed = 0;
  union bpf_attr lookup_attr;
  std::memset(&lookup_attr, 0, sizeof(lookup_attr));
  lookup_attr.map_fd = static_cast<std::uint32_t>(map_fd);
  lookup_attr.key = ptr_to_u64(&key);
  lookup_attr.value = ptr_to_u64(&observed);
  if (bpf_syscall(BPF_MAP_LOOKUP_ELEM, &lookup_attr) < 0) {
    close(map_fd);
    return kernel_test::fail("bpf_map_lookup");
  }

  kernel_test::metric("bpf_map_create_us", kernel_test::micros_since(create_start));
  kernel_test::metric("bpf_map_fd", map_fd);
  kernel_test::metric("bpf_observed_value", observed);

  close(map_fd);

  if (observed != value) {
    return kernel_test::fail_message("bpf_value_check", "lookup value did not match the write");
  }
  return kernel_test::pass("ebpf_smoke");
}
