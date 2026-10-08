<#
.SYNOPSIS
Packages Demon's Souls for Windows: the RPCS3 build, the Demon's Souls patches and the
launcher, frozen with PyInstaller so players need no Python.

.DESCRIPTION
Run from the repository root after building RPCS3 (scripts\win_build.ps1 or Visual Studio):

    .\demons_souls\packaging\package.ps1
    .\demons_souls\packaging\package.ps1 -BinDir .\bin -Python C:\Python313\python.exe

Output: out\DemonsSouls\ and out\DemonsSouls-windows-x64.zip.
#>
param(
    # Folder with rpcs3.exe; found automatically among the usual build outputs when empty.
    [string]$BinDir = "",
    # A Windows Python 3.10+ (python.org) used to freeze the launcher.
    [string]$Python = "",
    [string]$OutDir = "out",
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Project = Join-Path $Root "demons_souls"
$OutDir = Join-Path $Root $OutDir

function Find-Bin {
    foreach ($candidate in @("build\bin", "bin", "build-msvc\bin")) {
        $path = Join-Path $Root $candidate
        if (Test-Path (Join-Path $path "rpcs3.exe")) { return $path }
    }
    throw "rpcs3.exe not found in build\bin, bin or build-msvc\bin. Build RPCS3 first or pass -BinDir."
}

function Find-Python {
    $candidates = @()
    $candidates += Get-ChildItem "C:\Python3*\python.exe" -ErrorAction SilentlyContinue
    $candidates += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue
    if ($candidates.Count -eq 0) {
        throw "Need a Windows Python 3.10+ from python.org, or pass -Python path\to\python.exe."
    }
    return ($candidates | Sort-Object FullName | Select-Object -Last 1).FullName
}

if (-not $BinDir) { $BinDir = Find-Bin }
$BinDir = (Resolve-Path $BinDir).Path
if (-not (Test-Path (Join-Path $BinDir "rpcs3.exe"))) { throw "No rpcs3.exe in $BinDir" }
if (-not $Python) { $Python = Find-Python }
Write-Host "RPCS3 build: $BinDir"
Write-Host "Python:      $Python"

# Launcher tests first: no point shipping a broken launcher.
& $Python -m unittest discover -s (Join-Path $Project "launcher\tests")
if ($LASTEXITCODE -ne 0) { throw "Launcher tests failed" }

# Private venv with PyInstaller.
$Venv = Join-Path $OutDir "pyenv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $Python -m venv $Venv
    & $VenvPython -m pip install --quiet --upgrade pip pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "Could not install PyInstaller" }
}

$Package = Join-Path $OutDir "DemonsSouls"
if (Test-Path $Package) { Remove-Item -Recurse -Force $Package }
New-Item -ItemType Directory -Force $Package | Out-Null

# RPCS3 itself, without user data that a developer build may have collected.
$skip = @("config", "dev_hdd0", "dev_hdd1", "dev_flash", "dev_flash2", "dev_flash3", "dev_usb000", "cache", "log", "patches", "savestates", "captures", "screenshots", "games")
Get-ChildItem $BinDir | Where-Object { $skip -notcontains $_.Name -and $_.Extension -ne ".log" -and $_.Extension -ne ".pdb" } |
    Copy-Item -Destination $Package -Recurse

# Demon's Souls patches, loaded by RPCS3 from <exe dir>\patches\patch.yml.
New-Item -ItemType Directory -Force (Join-Path $Package "patches") | Out-Null
Copy-Item (Join-Path $Project "patches\patch.yml") (Join-Path $Package "patches\patch.yml")

# Launcher executables.
$Work = Join-Path $OutDir "pybuild"
$Icon = Join-Path $Project "launcher\demons_souls.ico"
$iconArgs = @()
if (Test-Path $Icon) {
    $iconArgs = @("--icon", $Icon, "--add-data", "$Icon;.")
    Copy-Item $Icon $Package
}
foreach ($entry in @(@("des_launcher.py", "Demons Souls"), @("des_play.py", "Play Demons Souls"))) {
    & $VenvPython -m PyInstaller --noconfirm --onefile --windowed --clean `
        --name $entry[1] --distpath $Package --workpath $Work --specpath $Work `
        --paths (Join-Path $Project "launcher") @iconArgs (Join-Path $Project "launcher\$($entry[0])")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $($entry[0])" }
}

Copy-Item (Join-Path $Project "packaging\README-Windows.txt") $Package
Copy-Item (Join-Path $Root "LICENSE") (Join-Path $Package "LICENSE.txt")

if (-not $NoZip) {
    $Zip = Join-Path $OutDir "DemonsSouls-windows-x64.zip"
    if (Test-Path $Zip) { Remove-Item -Force $Zip }
    Compress-Archive -Path $Package -DestinationPath $Zip
    Write-Host "Package: $Zip"
}
Write-Host "Folder:  $Package"
