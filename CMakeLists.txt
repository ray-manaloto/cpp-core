cmake_minimum_required(VERSION 3.31)

include(cmake/prelude.cmake)

project(
    cpp-core
    VERSION 0.1.0
    LANGUAGES CXX
)

include(cmake/project-is-top-level.cmake)
include(cmake/variables.cmake)

find_package(intel-cib CONFIG REQUIRED)
find_package(quill CONFIG REQUIRED)

# Logging: cib's logging interface with quill as the logger. The logging::config<> specialization
# lives in the header, so every translation unit that logs includes it and links this target.
add_library(cpp-core-logging STATIC src/logging/cib_quill.cpp)
add_library(cpp-core::logging ALIAS cpp-core-logging)
target_compile_features(cpp-core-logging PUBLIC cxx_std_26)
target_include_directories(cpp-core-logging PUBLIC "${PROJECT_SOURCE_DIR}/include")
target_link_libraries(cpp-core-logging PUBLIC intel::cib quill::quill)

# Main executable. The current main doubles as the C++26 static-reflection smoke test that
# ctest runs as cpp-core-smoke; replace it when the real project takes shape.
add_executable(cpp-core src/main.cpp)
target_compile_features(cpp-core PRIVATE cxx_std_26)
target_link_libraries(cpp-core PRIVATE cpp-core::logging)

if(cpp_core_DEVELOPER_MODE)
  include(cmake/dev-mode.cmake)
endif()
