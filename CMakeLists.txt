cmake_minimum_required(VERSION 3.28)

project(cpp_playground LANGUAGES C CXX)

include(CMakeParseArguments)
include(CTest)

enable_testing()

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(add_cpp_playground_test target source)
  set(options)
  set(one_value_args)
  set(multi_value_args LABELS LIBS)
  cmake_parse_arguments(TEST "${options}" "${one_value_args}" "${multi_value_args}" ${ARGN})

  add_executable(${target} ${source})
  target_compile_features(${target} PRIVATE cxx_std_23)
  target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)

  if(TEST_LIBS)
    target_link_libraries(${target} PRIVATE ${TEST_LIBS})
  endif()

  add_test(NAME ${target} COMMAND ${target})

  if(TEST_LABELS)
    set_tests_properties(${target} PROPERTIES LABELS "${TEST_LABELS}")
  endif()
endfunction()

add_cpp_playground_test(toolchain_smoke tests/toolchain_smoke.cpp LABELS toolchain)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  add_cpp_playground_test(
    shared_memory_smoke
    tests/kernel/shared_memory_smoke.cpp
    LABELS "kernel;shared-memory"
    LIBS rt
  )
  add_cpp_playground_test(epoll_smoke tests/kernel/epoll_smoke.cpp LABELS "kernel;epoll")
  add_cpp_playground_test(io_uring_smoke tests/kernel/io_uring_smoke.cpp LABELS "kernel;io_uring")
  add_cpp_playground_test(ebpf_smoke tests/kernel/ebpf_smoke.cpp LABELS "kernel;ebpf")
endif()
