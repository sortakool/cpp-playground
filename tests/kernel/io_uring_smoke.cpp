#include "test_support.hpp"

#include <linux/io_uring.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>

namespace {

int io_uring_setup_compat(unsigned entries, io_uring_params* params) {
  return static_cast<int>(syscall(SYS_io_uring_setup, entries, params));
}

int io_uring_enter_compat(int ring_fd, unsigned to_submit, unsigned min_complete, unsigned flags) {
  return static_cast<int>(
      syscall(SYS_io_uring_enter, ring_fd, to_submit, min_complete, flags, nullptr, 0));
}

}  // namespace

int main() {
  io_uring_params params{};
  const auto setup_start = kernel_test::clock::now();
  const int ring_fd = io_uring_setup_compat(8, &params);
  if (ring_fd < 0) {
    return kernel_test::fail("io_uring_setup");
  }

  const std::size_t sq_ring_size =
      params.sq_off.array + params.sq_entries * sizeof(std::uint32_t);
  const std::size_t cq_ring_size =
      params.cq_off.cqes + params.cq_entries * sizeof(io_uring_cqe);
  const std::size_t ring_map_size = std::max(sq_ring_size, cq_ring_size);

  void* sq_ring = mmap(nullptr, ring_map_size, PROT_READ | PROT_WRITE, MAP_SHARED, ring_fd,
                       IORING_OFF_SQ_RING);
  if (sq_ring == MAP_FAILED) {
    close(ring_fd);
    return kernel_test::fail("io_uring_mmap_sq");
  }

  void* cq_ring = sq_ring;
  if ((params.features & IORING_FEAT_SINGLE_MMAP) == 0U) {
    cq_ring = mmap(nullptr, cq_ring_size, PROT_READ | PROT_WRITE, MAP_SHARED, ring_fd,
                   IORING_OFF_CQ_RING);
    if (cq_ring == MAP_FAILED) {
      munmap(sq_ring, ring_map_size);
      close(ring_fd);
      return kernel_test::fail("io_uring_mmap_cq");
    }
  }

  auto* sqes = static_cast<io_uring_sqe*>(
      mmap(nullptr, params.sq_entries * sizeof(io_uring_sqe), PROT_READ | PROT_WRITE, MAP_SHARED,
           ring_fd, IORING_OFF_SQES));
  if (sqes == MAP_FAILED) {
    if (cq_ring != sq_ring) {
      munmap(cq_ring, cq_ring_size);
    }
    munmap(sq_ring, ring_map_size);
    close(ring_fd);
    return kernel_test::fail("io_uring_mmap_sqes");
  }

  auto* sq_tail =
      reinterpret_cast<std::uint32_t*>(static_cast<char*>(sq_ring) + params.sq_off.tail);
  auto* sq_mask =
      reinterpret_cast<std::uint32_t*>(static_cast<char*>(sq_ring) + params.sq_off.ring_mask);
  auto* sq_array =
      reinterpret_cast<std::uint32_t*>(static_cast<char*>(sq_ring) + params.sq_off.array);
  auto* cq_head =
      reinterpret_cast<std::uint32_t*>(static_cast<char*>(cq_ring) + params.cq_off.head);
  auto* cq_mask =
      reinterpret_cast<std::uint32_t*>(static_cast<char*>(cq_ring) + params.cq_off.ring_mask);
  auto* cqes =
      reinterpret_cast<io_uring_cqe*>(static_cast<char*>(cq_ring) + params.cq_off.cqes);

  const std::uint32_t tail = *sq_tail;
  const std::uint32_t index = tail & *sq_mask;
  std::memset(&sqes[index], 0, sizeof(io_uring_sqe));
  sqes[index].opcode = IORING_OP_NOP;
  sqes[index].user_data = 0xC0D3ULL;
  sq_array[index] = index;
  std::atomic_signal_fence(std::memory_order_seq_cst);
  *sq_tail = tail + 1;

  const auto submit_start = kernel_test::clock::now();
  if (io_uring_enter_compat(ring_fd, 1, 1, IORING_ENTER_GETEVENTS) < 0) {
    munmap(sqes, params.sq_entries * sizeof(io_uring_sqe));
    if (cq_ring != sq_ring) {
      munmap(cq_ring, cq_ring_size);
    }
    munmap(sq_ring, ring_map_size);
    close(ring_fd);
    return kernel_test::fail("io_uring_enter");
  }

  const io_uring_cqe& cqe = cqes[*cq_head & *cq_mask];
  kernel_test::metric("io_uring_setup_us", kernel_test::micros_since(setup_start));
  kernel_test::metric("io_uring_submit_us", kernel_test::micros_since(submit_start));
  kernel_test::metric("io_uring_cqe_res", cqe.res);
  kernel_test::metric("io_uring_user_data", cqe.user_data);

  *cq_head = *cq_head + 1;

  munmap(sqes, params.sq_entries * sizeof(io_uring_sqe));
  if (cq_ring != sq_ring) {
    munmap(cq_ring, cq_ring_size);
  }
  munmap(sq_ring, ring_map_size);
  close(ring_fd);

  if (cqe.res != 0 || cqe.user_data != 0xC0D3ULL) {
    return kernel_test::fail_message("io_uring_completion", "unexpected completion result");
  }
  return kernel_test::pass("io_uring_smoke");
}
