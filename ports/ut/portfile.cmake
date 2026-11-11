# Header-only. Upstream's own CMake builds the library and its module variant; this port installs
# the headers and writes a small CMake package of its own (ut::ut).
#
# The module variant (modules/ut.ixx) needs `import std`, which CMake only supports behind an
# experimental gate, so this port ships the header-only form: `#include "ut/ut.hpp"`.
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO stephenberry/ut
    REF dc65567be78febd265ca36c324e1c504512d4d74
    SHA512 e02212527bc75da3b356aa21307859b7367c3807dc5ca692d8ebe3ee4296c912ad0cbe202e9ea99ed2035240be98946fc4b8bfa23ec0be5e874432a9ce40b289
    HEAD_REF main
)

set(VCPKG_BUILD_TYPE release)  # headers only
file(INSTALL "${SOURCE_PATH}/include/ut" DESTINATION "${CURRENT_PACKAGES_DIR}/include")

file(WRITE "${CURRENT_PACKAGES_DIR}/share/${PORT}/${PORT}-config.cmake" [[
if(NOT TARGET ut::ut)
  get_filename_component(_prefix "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
  add_library(ut::ut INTERFACE IMPORTED)
  set_target_properties(ut::ut PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${_prefix}/include")
  unset(_prefix)
endif()
]])
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
