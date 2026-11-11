# The tests. They use ut (https://github.com/stephenberry/ut), the same way glaze does.
find_package(ut CONFIG REQUIRED)

# The test code is an object library, so that the string catalog tooling can scan it for the
# messages that need a catalog ID (see cmake/catalog.cmake).
add_library(cpp-core-test-code OBJECT logging_test.cpp)
target_compile_features(cpp-core-test-code PRIVATE cxx_std_26)
target_link_libraries(cpp-core-test-code PRIVATE cpp-core::logging ut::ut)

add_executable(cpp-core-tests)
target_sources(cpp-core-tests PRIVATE $<TARGET_OBJECTS:cpp-core-test-code>)
target_link_libraries(cpp-core-tests PRIVATE cpp-core::logging cpp-core-catalog)

add_test(NAME cpp-core-tests COMMAND cpp-core-tests)
