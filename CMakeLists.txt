cmake_minimum_required(VERSION 3.10)

set(CMAKE_CXX_STANDARD 20)

# Set the project name
project(eve-mapper)

# Add the cpp directory to the list of include directories
include_directories(${PROJECT_SOURCE_DIR}/cpp)

# Find all .cpp files in the cpp directory
file(GLOB CPP_SOURCES "${PROJECT_SOURCE_DIR}/cpp/*.cpp")

# Download stb_image_write.h and link it to the project
file(DOWNLOAD "https://raw.githubusercontent.com/nothings/stb/master/stb_image_write.h" "${PROJECT_SOURCE_DIR}/cpp/stb_image_write.h")

add_library(evemapper_lib STATIC
        cpp/Image.cpp
        cpp/Map.cpp
)

# Only for testing/autocomplete
if (false)
    find_package(PythonLibs QUIET)
    if (PYTHONLIBS_FOUND)
        message(STATUS "Python found")

        add_library(evemapper_pylib STATIC
            cpp/PyWrapper.cpp
            cpp/traceback_wrapper.cpp
        )

        include_directories(${PYTHON_INCLUDE_DIRS})
        target_link_libraries(evemapper_pylib ${PYTHON_LIBRARIES})
        target_link_libraries(evemapper_pylib evemapper_lib)
        add_compile_definitions(EVE_MAPPER_PYTHON)
    else()
        message(STATUS "Python not found")
    endif()
endif()

# Add the executable
add_executable(evemapper cpp/main.cpp)
add_compile_definitions(EVE_MAPPER_DEBUG_LOG)
add_compile_definitions(EVE_MAPPER_LINK_STB)
target_link_libraries(evemapper evemapper_lib)