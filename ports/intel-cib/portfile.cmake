# Header-only. Upstream's own CMake fetches its dependencies with CPM/FetchContent, so this port
# installs the headers and writes a small CMake package of its own (intel::cib).
#
# The port also installs the string-catalog tooling (cmake/string_catalog.cmake and the python
# script that drives it), so that a consumer can use cib's gen_str_catalog() to assign string IDs
# to its log messages and generate the catalog collateral (JSON/XML).
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO intel/compile-time-init-build
    REF b5c68e65801f0c4b6c83ef2d5fd49d3bb44dc75b
    SHA512 de3666a72e0b2a06aede1f8c51d0e12d1ddd2358927556ba07fce6a18fc88b4d529126971fabd7bf37f6538fc2bfdab94ab205a9ef1c357e99ead56907bfbd8c
    HEAD_REF main
)

set(VCPKG_BUILD_TYPE release)  # headers only
file(INSTALL "${SOURCE_PATH}/include/cib" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/flow" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/interrupt" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/log" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/log_binary" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/log_fmt" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/lookup" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/match" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/msg" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/nexus" DESTINATION "${CURRENT_PACKAGES_DIR}/include")
file(INSTALL "${SOURCE_PATH}/include/seq" DESTINATION "${CURRENT_PACKAGES_DIR}/include")

# The catalog tooling: the CMake wrapper function and the python script it drives.
file(INSTALL "${SOURCE_PATH}/cmake/string_catalog.cmake"
     DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
file(INSTALL "${SOURCE_PATH}/python/cib" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}/python")

file(WRITE "${CURRENT_PACKAGES_DIR}/share/${PORT}/${PORT}-config.cmake" [[
include(CMakeFindDependencyMacro)
find_dependency(intel-cpp-std-extensions CONFIG)
find_dependency(intel-baremetal-senders-and-receivers CONFIG)
find_dependency(intel-baremetal-concurrency CONFIG)
find_dependency(boost_mp11 CONFIG)
find_dependency(fmt CONFIG)
if(NOT TARGET intel::cib)
  get_filename_component(_prefix "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
  add_library(intel::cib INTERFACE IMPORTED)
  set_target_properties(intel::cib PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${_prefix}/include" INTERFACE_LINK_LIBRARIES "intel::stdx;intel::async;intel::concurrency;Boost::mp11;fmt::fmt")
  unset(_prefix)
endif()

# gen_str_catalog(): assigns string IDs to the log messages of a library and generates the
# catalog collateral. The python script it drives lives next to this file.
include("${CMAKE_CURRENT_LIST_DIR}/string_catalog.cmake")
set(intel_cib_GEN_STR_CATALOG "${CMAKE_CURRENT_LIST_DIR}/python/cib/gen_str_catalog.py")
]])
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
