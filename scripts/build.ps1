param(
    [ValidateSet('Debug', 'Release')]
    [string] $Configuration = 'Debug'
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPreset = 'windows-local-' + $Configuration.ToLowerInvariant()
$taskCmake = Join-Path $taskRoot '.tools/cmake/cmake/data/bin/cmake.exe'
$taskCtest = Join-Path $taskRoot '.tools/cmake/cmake/data/bin/ctest.exe'
if (-not (Test-Path -LiteralPath $taskCmake) -or
    -not (Test-Path -LiteralPath $taskCtest)) {
    throw 'Project-local tools are missing. See docs/ENVIRONMENT.md for setup.'
}

Push-Location -LiteralPath $taskRoot
try {
    & $taskCmake --preset $taskPreset
    if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed.' }
    & $taskCmake --build --preset $taskPreset
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    & $taskCtest --preset $taskPreset
    if ($LASTEXITCODE -ne 0) { throw 'CTest failed.' }
} finally {
    Pop-Location
}
