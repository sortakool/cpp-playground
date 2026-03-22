#include "test_support.hpp"

#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <unistd.h>

#include <cstdint>

int main() {
  const int epoll_fd = epoll_create1(EPOLL_CLOEXEC);
  if (epoll_fd < 0) {
    return kernel_test::fail("epoll_create1");
  }

  const int event_fd = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
  if (event_fd < 0) {
    close(epoll_fd);
    return kernel_test::fail("eventfd");
  }

  epoll_event interest{};
  interest.events = EPOLLIN;
  interest.data.fd = event_fd;
  if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, event_fd, &interest) != 0) {
    close(event_fd);
    close(epoll_fd);
    return kernel_test::fail("epoll_ctl_add");
  }

  const std::uint64_t signal_value = 7;
  if (write(event_fd, &signal_value, sizeof(signal_value)) != sizeof(signal_value)) {
    close(event_fd);
    close(epoll_fd);
    return kernel_test::fail("eventfd_write");
  }

  epoll_event ready{};
  const auto wait_start = kernel_test::clock::now();
  const int ready_count = epoll_wait(epoll_fd, &ready, 1, 1000);
  if (ready_count != 1) {
    close(event_fd);
    close(epoll_fd);
    return kernel_test::fail_message("epoll_wait", "expected exactly one ready event");
  }

  std::uint64_t observed_value = 0;
  if (read(event_fd, &observed_value, sizeof(observed_value)) != sizeof(observed_value)) {
    close(event_fd);
    close(epoll_fd);
    return kernel_test::fail("eventfd_read");
  }

  kernel_test::metric("epoll_wait_us", kernel_test::micros_since(wait_start));
  kernel_test::metric("epoll_ready_events", ready_count);
  kernel_test::metric("eventfd_value", observed_value);

  close(event_fd);
  close(epoll_fd);

  if ((ready.events & EPOLLIN) == 0 || observed_value != signal_value) {
    return kernel_test::fail_message("epoll_observation", "unexpected epoll or eventfd state");
  }
  return kernel_test::pass("epoll_smoke");
}
