cmake_minimum_required(VERSION 3.16)

project(
    ppm_edge_runtime
    VERSION 0.1.0
    LANGUAGES C
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(
    ppm_edge
    src/ppm_edge.c
)

target_include_directories(
    ppm_edge
    PUBLIC
    ${PROJECT_SOURCE_DIR}/src
)

add_executable(
    ppm_demo
    src/examples/basic.c
)

target_link_libraries(
    ppm_demo
    PRIVATE
    ppm_edge
)

enable_testing()
