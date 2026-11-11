# Header-only. Upstream's own CMake fetches its dependencies with CPM/FetchContent, so this port
# installs the headers and writes a small CMake package of its own (intel::concurrency).
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO intel/cpp-baremetal-concurrency
    REF 77be79110fd81bf6430ac5024f32895bb1b382a0
    SHA512 4bba307fc6868bb9d0dc54ac752684c395c44e98b0d65311e4f1fafcd72c44015a8456281038e8dce49d53f126aff1d7d701255459a2bbb5d547bebb4341c754
    HEAD_REF main
)

set(VCPKG_BUILD_TYPE release)  # headers only
file(INSTALL "${SOURCE_PATH}/include/conc" DESTINATION "${CURRENT_PACKAGES_DIR}/include")

file(WRITE "${CURRENT_PACKAGES_DIR}/share/${PORT}/${PORT}-config.cmake" [[
include(CMakeFindDependencyMacro)
if(NOT TARGET intel::concurrency)
  get_filename_component(_prefix "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
  add_library(intel::concurrency INTERFACE IMPORTED)
  set_target_properties(intel::concurrency PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${_prefix}/include")
  unset(_prefix)
endif()
]])
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
