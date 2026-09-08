cmake_minimum_required(VERSION 3.20)
project(AntennaSim VERSION 0.0.0 LANGUAGES CXX)

set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)

# Apply to our targets only; future third-party targets retain their own policy.
function(antennasim_target_defaults target)
    target_compile_features(${target} PUBLIC cxx_std_20)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /permissive- /fp:strict)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(${target} PRIVATE
            -Wall -Wextra -Wpedantic -Wconversion -Wshadow
            -fno-fast-math -ffp-contract=off)
    endif()
endfunction()

configure_file(src/version.hpp.in generated/antennasim/version.hpp @ONLY)
add_library(antennasim_core STATIC src/build_info.cpp src/grid.cpp src/fields.cpp src/vacuum.cpp)
add_library(AntennaSim::core ALIAS antennasim_core)
target_include_directories(antennasim_core
    PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include"
    PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
antennasim_target_defaults(antennasim_core)

# The reference kernel exists; simulation CLI commands remain REF-04 work.
add_executable(antennasim apps/main.cpp)
target_link_libraries(antennasim PRIVATE AntennaSim::core)
antennasim_target_defaults(antennasim)

if(BUILD_TESTING)
    add_executable(antennasim_toolchain_check tests/toolchain_check.cpp)
    target_link_libraries(antennasim_toolchain_check PRIVATE AntennaSim::core)
    antennasim_target_defaults(antennasim_toolchain_check)
    add_test(NAME foundation.toolchain COMMAND antennasim_toolchain_check)
    add_test(NAME foundation.cli_help COMMAND antennasim --help)
    set_tests_properties(foundation.cli_help PROPERTIES
        PASS_REGULAR_EXPRESSION "Simulation commands are not available yet")
    add_test(NAME foundation.cli_contract
        COMMAND "${CMAKE_COMMAND}"
        "-DAPP=$<TARGET_FILE:antennasim>"
        "-DEXPECTED_VERSION=${PROJECT_VERSION}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/cli_contract.cmake")
    set_tests_properties(foundation.toolchain foundation.cli_help
        foundation.cli_contract PROPERTIES LABELS "foundation;fast" TIMEOUT 10)

    add_executable(antennasim_grid_check tests/grid_check.cpp)
    target_link_libraries(antennasim_grid_check PRIVATE AntennaSim::core)
    antennasim_target_defaults(antennasim_grid_check)
    add_test(NAME reference.grid COMMAND antennasim_grid_check)
    set_tests_properties(reference.grid PROPERTIES
        LABELS "reference_structural;fast" TIMEOUT 10)

    add_executable(antennasim_fields_check tests/fields_check.cpp)
    target_link_libraries(antennasim_fields_check PRIVATE AntennaSim::core)
    antennasim_target_defaults(antennasim_fields_check)
    add_test(NAME reference.fields COMMAND antennasim_fields_check)
    set_tests_properties(reference.fields PROPERTIES
        LABELS "reference_structural;fast" TIMEOUT 10)

    add_executable(antennasim_vacuum_check tests/vacuum_check.cpp)
    target_link_libraries(antennasim_vacuum_check PRIVATE AntennaSim::core)
    antennasim_target_defaults(antennasim_vacuum_check)
    add_test(NAME reference.vacuum COMMAND antennasim_vacuum_check)
    set_tests_properties(reference.vacuum PROPERTIES
        LABELS "reference_structural;fast" TIMEOUT 10)
endif()
