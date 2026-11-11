enable_language(CXX)

set_property(GLOBAL PROPERTY USE_FOLDERS YES)

include(CTest)
if(BUILD_TESTING)
  add_subdirectory(tests)
endif()

# The include-what-you-use check. It is off by default, so that the normal builds are not slowed
# down; the p2996-iwyu preset turns it on.
option(CPP_CORE_IWYU_ENABLED "Run the include-what-you-use checks" OFF)
if(CPP_CORE_IWYU_ENABLED)
  include(cmake/iwyu.cmake)
endif()
