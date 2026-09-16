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
add_library(antennasim_core STATIC src/build_info.cpp src/grid.cpp src/fields.cpp src/vacuum.cpp src/run.cpp)
add_library(AntennaSim::core ALIAS antennasim_core)
target_include_directories(antennasim_core
    PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include"
    PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
antennasim_target_defaults(antennasim_core)

# Fingerprint actual source contents; CMake reconfigures when inputs change.
file(GLOB_RECURSE snapshot_inputs CONFIGURE_DEPENDS
    "include/*.hpp" "src/*.cpp" "src/*.in" "apps/*.cpp" "benchmarks/*.cpp" "benchmarks/*.hpp")
list(APPEND snapshot_inputs "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt" "${CMAKE_CURRENT_SOURCE_DIR}/CMakePresets.json")
list(SORT snapshot_inputs)
set(snapshot_text "")
foreach(input IN LISTS snapshot_inputs)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${input}")
    file(SHA256 "${input}" input_hash)
    file(RELATIVE_PATH input_name "${CMAKE_CURRENT_SOURCE_DIR}" "${input}")
    string(APPEND snapshot_text "${input_name}:${input_hash}\n")
endforeach()
string(SHA256 source_snapshot "${snapshot_text}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/source-snapshot.txt" "${snapshot_text}")
add_library(antennasim_benchmarks STATIC benchmarks/reference.cpp)
target_include_directories(antennasim_benchmarks PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/benchmarks")
target_link_libraries(antennasim_benchmarks PUBLIC AntennaSim::core)
target_compile_definitions(antennasim_benchmarks PRIVATE
    ANTENNASIM_SOURCE_SNAPSHOT="${source_snapshot}"
    ANTENNASIM_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
    ANTENNASIM_COMPILER="${CMAKE_CXX_COMPILER_ID}-${CMAKE_CXX_COMPILER_VERSION}-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}")
antennasim_target_defaults(antennasim_benchmarks)

add_executable(antennasim apps/main.cpp)
target_link_libraries(antennasim PRIVATE antennasim_benchmarks)
antennasim_target_defaults(antennasim)

if(BUILD_TESTING)
    # The independent Python audits are part of the validation contract. A
    # validation build must fail closed when its interpreter is unavailable.
    find_package(Python3 REQUIRED COMPONENTS Interpreter)

    add_executable(antennasim_toolchain_check tests/toolchain_check.cpp)
    target_link_libraries(antennasim_toolchain_check PRIVATE AntennaSim::core)
    antennasim_target_defaults(antennasim_toolchain_check)
    add_test(NAME foundation.toolchain COMMAND antennasim_toolchain_check)
    add_test(NAME foundation.cli_help COMMAND antennasim --help)
    set_tests_properties(foundation.cli_help PROPERTIES
        PASS_REGULAR_EXPRESSION "physical acceptance is not evaluated")
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

    add_executable(antennasim_run_check tests/run_check.cpp)
    target_link_libraries(antennasim_run_check PRIVATE antennasim_benchmarks)
    antennasim_target_defaults(antennasim_run_check)
    add_test(NAME reference.run COMMAND antennasim_run_check)
    set_tests_properties(reference.run PROPERTIES LABELS "reference_structural" TIMEOUT 120)

    add_test(NAME reference.yee_conventions COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_yee_conventions.py")
    add_test(NAME reference.benchmark_specification COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_reference_benchmarks.py")
    add_test(NAME reference.golden_steps COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_reference_steps.py")
    set_tests_properties(reference.yee_conventions reference.benchmark_specification
        reference.golden_steps PROPERTIES LABELS "reference_structural;analytical_audit;fast" TIMEOUT 30)

    add_test(NAME reference.run_artifacts COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_reference_runs.py"
        --app "$<TARGET_FILE:antennasim>" --output-root "${CMAKE_CURRENT_BINARY_DIR}/ref04-audits")
    set_tests_properties(reference.run_artifacts PROPERTIES LABELS "reference_structural" TIMEOUT 120)

    add_test(NAME reference.analysis_reductions COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/check_reference_analysis.py"
        --app "$<TARGET_FILE:antennasim>" --output-root "${CMAKE_CURRENT_BINARY_DIR}/ref05-audits")
    set_tests_properties(reference.analysis_reductions PROPERTIES
        LABELS "reference_structural;analytical_audit" TIMEOUT 300)
endif()
