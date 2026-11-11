# Header-only. Upstream's own CMake fetches its dependencies with CPM/FetchContent, so this port
# installs the headers and writes a small CMake package of its own (intel::async).
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO intel/cpp-baremetal-senders-and-receivers
    REF 5629659b781b0eaa51faf33363303737a695066c
    SHA512 71316b412e17e5b4b475a9993bbcce734eea7c39d9da1e65a92e1bd6e03f3510e5a647e76286309cc5f838b8bb2e6012dde63e60cc3e933dd476e6fa7374c876
    HEAD_REF main
)

set(VCPKG_BUILD_TYPE release)  # headers only
file(INSTALL "${SOURCE_PATH}/include/async" DESTINATION "${CURRENT_PACKAGES_DIR}/include")

file(WRITE "${CURRENT_PACKAGES_DIR}/share/${PORT}/${PORT}-config.cmake" [[
include(CMakeFindDependencyMacro)
find_dependency(intel-cpp-std-extensions CONFIG)
find_dependency(boost_mp11 CONFIG)
find_dependency(intel-baremetal-concurrency CONFIG)
if(NOT TARGET intel::async)
  get_filename_component(_prefix "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
  add_library(intel::async INTERFACE IMPORTED)
  set_target_properties(intel::async PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${_prefix}/include" INTERFACE_LINK_LIBRARIES "intel::stdx;Boost::mp11;intel::concurrency")
  unset(_prefix)
endif()
]])
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
