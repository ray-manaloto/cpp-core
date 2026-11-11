# The string catalog.
#
# cib's gen_str_catalog() tooling (from the intel-cib port) assigns a string ID to every log
# message and a module ID to every module, and generates the catalog collateral (JSON and XML).
#
# How it works:
# - the logging library refers to catalog<Message>() and module<Module>(), whose definitions only
#   exist in the generated file;
# - the undefined symbols of the libraries that log are extracted with nm;
# - the tooling turns them into the specializations (the IDs) and into the collateral.
#
# The generated file is compiled into the cpp-core-catalog library, which the executables link.

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# The libraries that contain the log calls. Every message in them gets a catalog ID.
set(cpp_core_catalog_inputs cpp-core-app)
if(TARGET cpp-core-test-code)
  list(APPEND cpp_core_catalog_inputs cpp-core-test-code)
endif()

gen_str_catalog(
    OUTPUT_CPP
    ${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.cpp
    OUTPUT_JSON
    ${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.json
    OUTPUT_XML
    ${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.xml
    INPUT_LIBS
    ${cpp_core_catalog_inputs}
    GEN_STR_CATALOG
    ${intel_cib_GEN_STR_CATALOG}
    CLIENT_NAME
    cpp-core
    VERSION
    ${PROJECT_VERSION}
    OUTPUTS_TARGET
    cpp-core-catalog-outputs
)

add_library(cpp-core-catalog STATIC ${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.cpp)
target_link_libraries(cpp-core-catalog PUBLIC intel::cib)
