cmake_minimum_required(VERSION 3.31)

include(cmake/prelude.cmake)

project(
    cpp-core
    VERSION 0.1.0
    LANGUAGES CXX
)

include(cmake/project-is-top-level.cmake)
include(cmake/variables.cmake)

# Main executable. The current main doubles as the C++26 static-reflection smoke test that
# ctest runs as cpp-core-smoke; replace it when the real project takes shape.
add_executable(cpp-core src/main.cpp)
target_compile_features(cpp-core PRIVATE cxx_std_26)

if(cpp_core_DEVELOPER_MODE)
  include(cmake/dev-mode.cmake)
endif()
