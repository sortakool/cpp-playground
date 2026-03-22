#pragma once

#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string_view>

namespace kernel_test {

using clock = std::chrono::steady_clock;

inline long long micros_since(clock::time_point start) {
  return std::chrono::duration_cast<std::chrono::microseconds>(clock::now() - start).count();
}

template <typename T>
inline void metric(std::string_view name, const T& value) {
  std::cout << name << '=' << value << '\n';
}

inline int fail(std::string_view step) {
  std::cerr << "FAIL step=" << step << " errno=" << errno
            << " message=" << std::strerror(errno) << '\n';
  return EXIT_FAILURE;
}

inline int fail_message(std::string_view step, std::string_view message) {
  std::cerr << "FAIL step=" << step << " message=" << message << '\n';
  return EXIT_FAILURE;
}

inline int pass(std::string_view name) {
  std::cout << "PASS " << name << '\n';
  return EXIT_SUCCESS;
}

}  // namespace kernel_test
