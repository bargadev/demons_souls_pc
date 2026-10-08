<#
.SYNOPSIS
Builds RPCS3 (Release x64) with the Visual Studio solution and the precompiled LLVM libs.

.DESCRIPTION
Run from the repository root:

    .\demons_souls\packaging\build.ps1
    .\demons_souls\packaging\build.ps1 -QtDir C:\Qt\6.12.0\msvc2022_64 -Package

Needs Visual Studio 2022/2026 (Desktop development with C++), Qt 6.12 for MSVC (with Qt
Multimedia) and the Vulkan SDK. Output: bin\rpcs3.exe. -Package also runs package.ps1.
#>
param(
    # Qt for MSVC; defaults to QTDIR, Qt6_ROOT, or the newest C:\Qt\6.*\msvc20*_64.
    [string]$QtDir = "",
    [int]$Cores = [Environment]::ProcessorCount,
    [switch]$Package
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Find-Qt {
    foreach ($candidate in @($env:QTDIR, $env:Qt6_ROOT)) {
        if ($candidate -and (Test-Path (Join-Path $candidate "bin\windeployqt6.exe"))) { return $candidate }
    }
    $found = Get-ChildItem "C:\Qt\6.*\msvc20*_64" -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName "bin\windeployqt6.exe") } |
        Sort-Object FullName | Select-Object -Last 1
    if ($found) { return $found.FullName }
    throw "Qt for MSVC not found. Install Qt 6.12 (msvc2022_64 + Qt Multimedia) or pass -QtDir."
}

function Find-MSBuild {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) { throw "Visual Studio not found (no vswhere.exe). Install VS 2022/2026 with C++." }
    $msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" | Select-Object -First 1
    if (-not $msbuild) { throw "MSBuild not found. Install the 'Desktop development with C++' workload." }
    return $msbuild
}

if (-not $env:VULKAN_SDK) { throw "VULKAN_SDK is not set. Install the Vulkan SDK and open a new terminal." }
if (-not $QtDir) { $QtDir = Find-Qt }
$MSBuild = Find-MSBuild

if (-not (Test-Path (Join-Path $Root "3rdparty\llvm\llvm\llvm"))) {
    Write-Host "Fetching submodules..."
    git -C $Root submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw "git submodule update failed" }
}

$llvm = Join-Path $Root "build\lib_ext\Release-x64\llvm_build"
if (-not (Test-Path $llvm)) {
    Write-Warning "Precompiled LLVM libs missing in build\lib_ext\Release-x64; the build will compile LLVM (slow). See BUILDING.md."
}

Write-Host "Qt:      $QtDir"
Write-Host "Vulkan:  $env:VULKAN_SDK"
Write-Host "MSBuild: $MSBuild"

$env:QTDIR = $QtDir
& $MSBuild (Join-Path $Root "rpcs3.sln") /m:$Cores /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo
if ($LASTEXITCODE -ne 0) { throw "Build failed" }

$exe = Join-Path $Root "bin\rpcs3.exe"
if (-not (Test-Path $exe)) { throw "Build finished but $exe is missing" }
Write-Host "Built: $exe"

if ($Package) {
    & (Join-Path $PSScriptRoot "package.ps1") -BinDir (Join-Path $Root "bin")
}
