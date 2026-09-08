execute_process(COMMAND "${APP}" --version
    RESULT_VARIABLE status OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT status STREQUAL "0" OR NOT output STREQUAL "AntennaSim ${EXPECTED_VERSION}\n"
        OR NOT error STREQUAL "")
    message(FATAL_ERROR "Unexpected version response: ${status}: ${output} ${error}")
endif()

# Fail explicitly if an unsupported simulation request is accidentally accepted.
execute_process(COMMAND "${APP}" simulate
    RESULT_VARIABLE status OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT status STREQUAL "2" OR NOT output STREQUAL ""
        OR NOT error MATCHES "Unsupported arguments")
    message(FATAL_ERROR "Unsupported request must fail explicitly: ${status}: ${output} ${error}")
endif()
