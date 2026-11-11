# Runs after project() through CMAKE_PROJECT_INCLUDE (set by the cpp-core presets).
# Refuses a configure whose compiler is not the one CPP_CORE_COMPILER names, so a preset can never
# silently build with whatever clang++ or g++ happens to be first on PATH. Then adds the reflection
# flags for this project's C++ (the toolchain keeps them out of CMAKE_CXX_FLAGS on purpose).

include_guard(GLOBAL)

if(NOT DEFINED CPP_CORE_COMPILER OR NOT CMAKE_CXX_COMPILER_LOADED)
  return()
endif()

set(_id "${CMAKE_CXX_COMPILER_ID}")
set(_ver "${CMAKE_CXX_COMPILER_VERSION}")
set(_path "${CMAKE_CXX_COMPILER}")  # full path: a p2996 build may install a plain clang++ under a p2996 dir
set(_ok FALSE)
if(CPP_CORE_COMPILER STREQUAL "gcc16")
  if(_id STREQUAL "GNU" AND _ver VERSION_GREATER_EQUAL 16 AND _ver VERSION_LESS 17)
    set(_ok TRUE)
  endif()
  set(_want "GCC 16")
elseif(CPP_CORE_COMPILER STREQUAL "clang23")
  if(_id STREQUAL "Clang" AND _ver VERSION_GREATER_EQUAL 23 AND _ver VERSION_LESS 24 AND NOT _path MATCHES "p2996")
    set(_ok TRUE)
  endif()
  set(_want "LLVM clang 23 (not Apple clang, not clang-p2996)")
elseif(CPP_CORE_COMPILER STREQUAL "p2996")
  if(_id STREQUAL "Clang" AND _path MATCHES "p2996")
    set(_ok TRUE)
  endif()
  set(_want "clang-p2996 (bloomberg/clang-p2996)")
endif()

if(NOT _ok)
  message(FATAL_ERROR
    "CPP_CORE_COMPILER=${CPP_CORE_COMPILER} wants ${_want}, but CMake found "
    "${_id} ${_ver} at ${CMAKE_CXX_COMPILER}. Fix PATH, or set CPP_CORE_CXX and CPP_CORE_CC (see README.md).")
endif()

# Reflection flags (set by the toolchain in CPP_CORE_REFLECTION_FLAGS) for this project's C++ only.
foreach(_flag IN LISTS CPP_CORE_REFLECTION_FLAGS)  # one generator expression per flag
  add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:${_flag}>")
endforeach()
message(STATUS "cpp-core: ${CPP_CORE_COMPILER} = ${_id} ${_ver} (${CMAKE_CXX_COMPILER}), "
               "sanitizer ${CPP_CORE_SANITIZER}, hardening ${CPP_CORE_HARDENING}, reflection [${CPP_CORE_REFLECTION_FLAGS}]")
