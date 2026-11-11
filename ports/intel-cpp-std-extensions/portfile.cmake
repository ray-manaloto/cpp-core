# Header-only. Upstream's own CMake fetches its dependencies with CPM/FetchContent, so this port
# installs the headers and writes a small CMake package of its own (intel::stdx).
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO intel/cpp-std-extensions
    REF 94546c5a9122b99dc671cbefd7cfec168108febe
    SHA512 395f3c21d1a4727877deaff793ace8362b1e45f3886787f7470b5dac22b65b0bf1b54b57786a7ac1cd60c1b37422c9bc56630b95f46c39307c4de64f01f51c49
    HEAD_REF main
)

set(VCPKG_BUILD_TYPE release)  # headers only
file(INSTALL "${SOURCE_PATH}/include/stdx" DESTINATION "${CURRENT_PACKAGES_DIR}/include")

file(WRITE "${CURRENT_PACKAGES_DIR}/share/${PORT}/${PORT}-config.cmake" [[
include(CMakeFindDependencyMacro)
find_dependency(boost_mp11 CONFIG)
find_dependency(fmt CONFIG)
find_dependency(intel-baremetal-concurrency CONFIG)
if(NOT TARGET intel::stdx)
  get_filename_component(_prefix "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
  add_library(intel::stdx INTERFACE IMPORTED)
  set_target_properties(intel::stdx PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${_prefix}/include" INTERFACE_LINK_LIBRARIES "Boost::mp11;fmt::fmt;intel::concurrency")
  unset(_prefix)
endif()
]])
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
