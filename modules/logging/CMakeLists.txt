# The logging library: the com.rsm.logging module.
#
# The module's interface unit carries the public API. The quill logger (the implementation that
# both logging paths share) is a regular source file of the same library: a module's interface
# cannot depend on the standard library (see the comment at the top of logging.cppm), so the
# module reaches the implementation through the standard-library-free interface in
# cpp-core/logging/internal.hpp.
add_library(cpp-core-logging STATIC)
add_library(cpp-core::logging ALIAS cpp-core-logging)

target_compile_features(cpp-core-logging PUBLIC cxx_std_26)

target_sources(
    cpp-core-logging
    PUBLIC
        FILE_SET CXX_MODULES FILES logging.cppm
    PRIVATE
        ${PROJECT_SOURCE_DIR}/src/logging/quill_logger.cpp
        format.hpp
)

target_include_directories(cpp-core-logging PUBLIC "${PROJECT_SOURCE_DIR}/include")
target_link_libraries(cpp-core-logging PUBLIC intel::cib quill::quill)
