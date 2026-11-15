# Include-what-you-use (IWYU).
#
# IWYU parses a translation unit and reports the includes that are missing or superfluous. It is a
# clang tool, so it needs a compiler that understands the code, and it needs the flags of the
# translation unit that it checks.
#
# The `iwyu` target runs the checks:
#   cmake --build --preset p2996-iwyu
#
# The check is off by default, so that the normal builds are not slowed down. The p2996-iwyu
# preset turns it on.

include_guard(GLOBAL)

find_program(CPP_CORE_IWYU_EXECUTABLE NAMES include-what-you-use)

if(NOT CPP_CORE_IWYU_EXECUTABLE)
  message(
    FATAL_ERROR
    "include-what-you-use was not found. Install it (brew install include-what-you-use), or "
    "turn the check off (CPP_CORE_IWYU_ENABLED=OFF)."
  )
endif()

# The flags that every check uses. The include directories are the ones of the project and of the
# installed ports (vcpkg puts them in the include directory of the triplet).
set(
  CPP_CORE_IWYU_FLAGS
  -std=c++26
  "-I${PROJECT_SOURCE_DIR}/include"
  "-isystem${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}/include"
  -Xiwyu
  "--mapping_file=${PROJECT_SOURCE_DIR}/cmake/iwyu_mappings.txt"
  -Xiwyu
  "--error"
)

# The translation units that are checked.
set(
  CPP_CORE_IWYU_SOURCES
  "${PROJECT_SOURCE_DIR}/modules/logging/logging.cppm"
  "${PROJECT_SOURCE_DIR}/src/app.cpp"
  "${PROJECT_SOURCE_DIR}/src/logging/quill_logger.cpp"
)

# The translation units that are not checked, and why. These are limitations of the tool, not
# defects of the code:
#
# - IWYU crashes when a translation unit imports a module that has a class with a user-declared
#   constructor (the logging module has one: the format_string class template). The check on the
#   module interface itself covers the includes of the module; the consumers of the module have
#   nothing but the import and the names of the logging functions.
# - The reflection demo needs the reflection header (<meta>), which is not part of the standard
#   library that IWYU's compiler (Homebrew's clang) uses yet.
set(
  CPP_CORE_IWYU_SKIPPED_SOURCES
  "${PROJECT_SOURCE_DIR}/src/main.cpp"
  "${PROJECT_SOURCE_DIR}/src/reflection_demo.cpp"
  "${PROJECT_SOURCE_DIR}/tests/logging_test.cpp"
)

set(
  CPP_CORE_IWYU_SKIP_REASONS
  "IWYU crashes on a module import"
  "<meta> is not in IWYU's standard library"
  "IWYU crashes on a module import"
)

list(LENGTH CPP_CORE_IWYU_SKIPPED_SOURCES skipped_count)
list(LENGTH CPP_CORE_IWYU_SKIP_REASONS reason_count)
if(NOT skipped_count EQUAL reason_count)
  message(FATAL_ERROR "The skipped sources and their reasons do not match.")
endif()

math(EXPR skipped_last "${skipped_count} - 1")
foreach(index RANGE ${skipped_last})
  list(GET CPP_CORE_IWYU_SKIPPED_SOURCES ${index} skipped_source)
  list(GET CPP_CORE_IWYU_SKIP_REASONS ${index} skipped_reason)
  message(STATUS "include-what-you-use: skipping ${skipped_source} (${skipped_reason})")
endforeach()

# Every check is its own target, so that a check that fails does not stop the other ones.
set(CPP_CORE_IWYU_CHECK_TARGETS "")
foreach(source IN LISTS CPP_CORE_IWYU_SOURCES)
  string(MAKE_C_IDENTIFIER "iwyu-${source}" check_name)

  add_custom_target(
    ${check_name}
    COMMAND "${CPP_CORE_IWYU_EXECUTABLE}" ${CPP_CORE_IWYU_FLAGS} "${source}"
    COMMENT "include-what-you-use: ${source}"
    USES_TERMINAL
    VERBATIM
  )
  list(APPEND CPP_CORE_IWYU_CHECK_TARGETS ${check_name})
endforeach()

add_custom_target(iwyu DEPENDS ${CPP_CORE_IWYU_CHECK_TARGETS})
