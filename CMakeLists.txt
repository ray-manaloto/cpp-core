cmake_minimum_required(VERSION 3.31)

include(cmake/prelude.cmake)

project(cpp-core VERSION 0.1.0 LANGUAGES CXX)

include(cmake/project-is-top-level.cmake)
include(cmake/variables.cmake)

find_package(intel-cib CONFIG REQUIRED)
find_package(quill CONFIG REQUIRED)

# The modular libraries: each library is a C++ module.
add_subdirectory(modules)

# The application. The log calls live in an object library (and not in main.cpp), so that the
# string catalog tooling can scan them for the catalog IDs (see cmake/catalog.cmake).
add_library(cpp-core-app OBJECT src/app.cpp src/reflection_demo.cpp)
target_compile_features(cpp-core-app PRIVATE cxx_std_26)
target_link_libraries(cpp-core-app PRIVATE cpp-core::logging)

add_executable(cpp-core src/main.cpp)
target_compile_features(cpp-core PRIVATE cxx_std_26)
target_link_libraries(cpp-core PRIVATE cpp-core-app cpp-core::logging cpp-core-catalog)

if(cpp_core_DEVELOPER_MODE)
  include(cmake/dev-mode.cmake)
endif()

# The string catalog: the IDs of the log messages of the application and of the tests.
include(cmake/catalog.cmake)
