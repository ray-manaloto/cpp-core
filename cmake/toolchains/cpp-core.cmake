# Toolchain for the cpp-core presets (cmake/presets/cpp-core.json) and the vcpkg triplets in triplets/.
#
# One file for every compiler. The preset (or the triplet, for vcpkg's own port builds) picks the
# compiler and the variants through cache variables:
#   CPP_CORE_COMPILER   gcc16 | clang23 | p2996
#   CPP_CORE_SANITIZER  none | asan | tsan   (asan = AddressSanitizer + UndefinedBehaviorSanitizer;
#                        tsan = ThreadSanitizer; GCC 16 supports it on Linux only, as it has no
#                        TSan runtime on macOS)
#   CPP_CORE_HARDENING  none | fast | extensive | debug
#                        libc++ (_LIBCPP_HARDENING_MODE) on the clang compilers; on GCC anything but
#                        none turns on _GLIBCXX_ASSERTIONS. Set it explicitly: the clang-p2996 libc++
#                        defaults to extensive and Homebrew's to none, which skews any comparison.
#
# Compilers are bare names found on PATH (mise and Homebrew provide them); no machine path is written
# here. To use a compiler outside PATH, set the environment variables CPP_CORE_CXX and CPP_CORE_CC
# (for example in a gitignored CMakeUserPresets.json). They reach both this project and vcpkg's port
# builds, because the triplets pass them through (VCPKG_ENV_PASSTHROUGH). cmake/cpp-core-check.cmake
# then refuses a compiler that is not the one CPP_CORE_COMPILER names.

include_guard(GLOBAL)

set(CPP_CORE_COMPILER "gcc16" CACHE STRING "Compiler: gcc16, clang23 or p2996")
set(CPP_CORE_SANITIZER "none" CACHE STRING "Sanitizer: none, asan or tsan")
set(CPP_CORE_HARDENING "none" CACHE STRING "Standard library hardening: none, fast, extensive or debug")
set_property(CACHE CPP_CORE_COMPILER PROPERTY STRINGS gcc16 clang23 p2996)
set_property(CACHE CPP_CORE_SANITIZER PROPERTY STRINGS none asan tsan)
set_property(CACHE CPP_CORE_HARDENING PROPERTY STRINGS none fast extensive debug)

# try_compile projects re-read this file; pass the choices through to them.
list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES CPP_CORE_COMPILER CPP_CORE_SANITIZER CPP_CORE_HARDENING CPP_CORE_PORT_BUILD CPP_CORE_EXTRA_CXX_FLAGS)

set(_cpp_core_flags "")        # C and C++
set(_cpp_core_cxx_only "")     # C++ only
set(_cpp_core_link "")
set(_cpp_core_reflection "")
if(CPP_CORE_COMPILER STREQUAL "gcc16")
  set(_cpp_core_cxx g++-16)
  set(_cpp_core_c gcc-16)
  set(_cpp_core_reflection -freflection)
  set(_cpp_core_libcxx OFF)
elseif(CPP_CORE_COMPILER STREQUAL "clang23")
  set(_cpp_core_cxx clang++)
  set(_cpp_core_c clang)
  set(_cpp_core_libcxx ON)
elseif(CPP_CORE_COMPILER STREQUAL "p2996")
  set(_cpp_core_cxx clang++-p2996)
  set(_cpp_core_c clang-p2996)
  set(_cpp_core_reflection -freflection -fexpansion-statements -fannotation-attributes)
  set(_cpp_core_libcxx ON)
else()
  message(FATAL_ERROR "CPP_CORE_COMPILER must be gcc16, clang23 or p2996, not '${CPP_CORE_COMPILER}'")
endif()

if(DEFINED ENV{CPP_CORE_CXX} AND NOT "$ENV{CPP_CORE_CXX}" STREQUAL "")
  set(_cpp_core_cxx "$ENV{CPP_CORE_CXX}")
endif()
if(DEFINED ENV{CPP_CORE_CC} AND NOT "$ENV{CPP_CORE_CC}" STREQUAL "")
  set(_cpp_core_c "$ENV{CPP_CORE_CC}")
endif()
if(NOT CMAKE_CXX_COMPILER)
  set(CMAKE_CXX_COMPILER "${_cpp_core_cxx}")
endif()
if(NOT CMAKE_C_COMPILER)
  set(CMAKE_C_COMPILER "${_cpp_core_c}")
endif()

# C++26 for the project. vcpkg port builds (the triplets pass CPP_CORE_PORT_BUILD=ON) keep each port's
# own standard: forcing C++26 on them turns on C++ module builds in some ports and can break them.
# A port that needs C++26 asks for it itself.
if(NOT DEFINED CMAKE_CXX_STANDARD AND NOT CPP_CORE_PORT_BUILD)
  set(CMAKE_CXX_STANDARD 26)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
endif()

# Reflection flags are not set here. GCC 16 refuses -freflection below -std=c++26, so a flag in
# CMAKE_CXX_FLAGS breaks every compile that is not C++26: vcpkg ports, CMake's compiler checks in
# nested projects, and any consumer that forwards CMAKE_CXX_FLAGS. The project adds them in
# cmake/cpp-core-check.cmake instead, and a port that needs them asks through
# CPP_CORE_EXTRA_CXX_FLAGS.
set(CPP_CORE_REFLECTION_FLAGS "${_cpp_core_reflection}")
# Extra C++ flags a port asks for.
if(CPP_CORE_EXTRA_CXX_FLAGS)
  list(APPEND _cpp_core_cxx_only ${CPP_CORE_EXTRA_CXX_FLAGS})
endif()

# vcpkg port builds. vcpkg passes CMAKE_SYSTEM_NAME to every CMake port configure when the triplet sets
# VCPKG_CMAKE_SYSTEM_NAME (all of ours do), which on its own makes CMake treat
# the build as cross-compiling (try_run refused, CMAKE_SYSTEM_PROCESSOR empty). vcpkg's own linux.cmake
# and osx.cmake undo that, and a chain-loaded toolchain replaces them, so do the same here: set the
# processor from the triplet's architecture and turn cross-compiling off when host and target match.
# On Linux also add -fPIC, as linux.cmake does, so static port libraries can be linked into shared
# libraries and PIE executables (macOS code is position-independent by default).
if(CPP_CORE_PORT_BUILD AND DEFINED VCPKG_TARGET_ARCHITECTURE)
  if(NOT DEFINED CMAKE_SYSTEM_PROCESSOR)
    if(VCPKG_TARGET_ARCHITECTURE STREQUAL "x64")
      set(CMAKE_SYSTEM_PROCESSOR x86_64 CACHE STRING "")
    elseif(VCPKG_TARGET_ARCHITECTURE STREQUAL "arm64" AND CMAKE_SYSTEM_NAME STREQUAL "Darwin")
      set(CMAKE_SYSTEM_PROCESSOR arm64 CACHE STRING "")
    elseif(VCPKG_TARGET_ARCHITECTURE STREQUAL "arm64")
      set(CMAKE_SYSTEM_PROCESSOR aarch64 CACHE STRING "")
    endif()
  endif()
  if(CMAKE_SYSTEM_NAME STREQUAL CMAKE_HOST_SYSTEM_NAME AND CMAKE_SYSTEM_PROCESSOR STREQUAL CMAKE_HOST_SYSTEM_PROCESSOR)
    set(CMAKE_CROSSCOMPILING OFF CACHE BOOL "")
  endif()
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    list(APPEND _cpp_core_flags -fPIC)
  endif()
endif()

if(_cpp_core_libcxx)
  list(APPEND _cpp_core_cxx_only -stdlib=libc++)
  list(APPEND _cpp_core_link -stdlib=libc++)
endif()

if(CPP_CORE_HARDENING STREQUAL "none")
  if(_cpp_core_libcxx)
    list(APPEND _cpp_core_cxx_only -D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_NONE)
  endif()
elseif(CPP_CORE_HARDENING MATCHES "^(fast|extensive|debug)$")
  if(_cpp_core_libcxx)
    string(TOUPPER "${CPP_CORE_HARDENING}" _cpp_core_mode)
    list(APPEND _cpp_core_cxx_only -D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_${_cpp_core_mode})
  else()
    list(APPEND _cpp_core_cxx_only -D_GLIBCXX_ASSERTIONS)
  endif()
else()
  message(FATAL_ERROR "CPP_CORE_HARDENING must be none, fast, extensive or debug, not '${CPP_CORE_HARDENING}'")
endif()

if(CPP_CORE_SANITIZER STREQUAL "asan")
  list(APPEND _cpp_core_flags -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=undefined)
  list(APPEND _cpp_core_link -fsanitize=address,undefined)
  # Third-party C ports call functions through mismatched pointer types on purpose; clang's
  # -fsanitize=function aborts on that. Our own code keeps it.
  if(CPP_CORE_PORT_BUILD AND NOT CPP_CORE_COMPILER STREQUAL "gcc16")
    list(APPEND _cpp_core_flags -fno-sanitize=function)
  endif()
  # GCC 16 bug: with -fsanitize=null, nonnull-attribute or returns-nonnull-attribute, a null check on a
  # pointer into a template parameter object is "not a constant expression", so valid constexpr code
  # (e.g. std::string_view::find on a string literal template argument) fails to compile.
  if(CPP_CORE_COMPILER STREQUAL "gcc16")
    list(APPEND _cpp_core_flags -fno-sanitize=null,nonnull-attribute,returns-nonnull-attribute)
  endif()
elseif(CPP_CORE_SANITIZER STREQUAL "tsan")
  # GCC's TSan runtime exists on Linux, not on macOS.
  if(CPP_CORE_COMPILER STREQUAL "gcc16" AND CMAKE_HOST_APPLE)
    message(FATAL_ERROR "GCC 16 on macOS has no ThreadSanitizer runtime (___tsan_* undefined at link); use p2996")
  endif()
  list(APPEND _cpp_core_flags -fsanitize=thread -fno-omit-frame-pointer)
  list(APPEND _cpp_core_link -fsanitize=thread)
elseif(NOT CPP_CORE_SANITIZER STREQUAL "none")
  message(FATAL_ERROR "CPP_CORE_SANITIZER must be none, asan or tsan, not '${CPP_CORE_SANITIZER}'")
endif()

list(JOIN _cpp_core_flags " " _cpp_core_common)
list(JOIN _cpp_core_cxx_only " " _cpp_core_cxx_extra)
list(JOIN _cpp_core_link " " _cpp_core_link_flags)
string(STRIP "${_cpp_core_common} ${_cpp_core_cxx_extra}" CMAKE_CXX_FLAGS_INIT)
set(CMAKE_C_FLAGS_INIT "${_cpp_core_common}")
foreach(_kind EXE SHARED MODULE)
  set(CMAKE_${_kind}_LINKER_FLAGS_INIT "${_cpp_core_link_flags}")
endforeach()
