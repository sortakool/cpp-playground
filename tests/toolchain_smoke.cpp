#include <cstdlib>
#include <iostream>

int main() {
  std::cout << "PASS toolchain_smoke\n";
  std::cout << "cplusplus=" << __cplusplus << '\n';

#if defined(__clang__)
  std::cout << "compiler=clang "
            << __clang_major__ << '.' << __clang_minor__ << '.' << __clang_patchlevel__
            << '\n';
#elif defined(__GNUC__)
  std::cout << "compiler=gcc " << __GNUC__ << '.' << __GNUC_MINOR__ << '.' << __GNUC_PATCHLEVEL__
            << '\n';
#else
  std::cout << "compiler=unknown\n";
#endif

#if defined(__GLIBCXX__)
  std::cout << "stdlib=libstdc++ " << __GLIBCXX__ << '\n';
#elif defined(_LIBCPP_VERSION)
  std::cout << "stdlib=libc++ " << _LIBCPP_VERSION << '\n';
#else
  std::cout << "stdlib=unknown\n";
#endif

  return EXIT_SUCCESS;
}
