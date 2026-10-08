# demons_souls/

Everything specific to the Demon's Souls build. The rest of the repository is RPCS3.

| Path | What |
|---|---|
| `launcher/des_core.py` | Game detection (PARAM.SFO), settings, RPCS3 config and `patch_config.yml` generation |
| `launcher/des_launcher.py` | Launcher window (tkinter); `--play` starts the game with saved settings |
| `launcher/des_play.py` | Entry point for `Play Demons Souls.exe` |
| `launcher/des_i18n.py` | Launcher strings (English, Portuguese) |
| `launcher/tests/` | Unit tests (standard library `unittest`) |
| `patches/patch.yml` | Demon's Souls section of the RPCS3 patch database |
| `tools/update_patches.py` | Refreshes `patches/patch.yml` from rpcs3.net |
| `packaging/build.ps1` | Builds RPCS3 with MSBuild (`rpcs3.sln`, Release x64) |
| `packaging/package.ps1` | Builds the player zip from an RPCS3 build |
| `packaging/README-Windows.txt` | Player instructions shipped in the zip |

## How a game start works

1. The launcher reads `PS3_GAME/PARAM.SFO` to find the serial and version.
2. It writes two files into `<exe dir>/config/`:
   - `demons_souls_config.yml`, a config override that RPCS3 applies over its defaults
     (`--config`): LLVM recompilers, Vulkan, resolution scale, FSR, VSync, wide screen
     stretching, auto exit.
   - `patch_config.yml`, the patches turned on for this serial and version: Unlock FPS,
     Skip Intro Videos, Disable Motion Blur, Aspect Ratio (and the HUD fix on the US disc).
3. It runs `rpcs3.exe --no-gui [--fullscreen] --config <override> <EBOOT.BIN>`.

RPCS3 on Windows keeps its data next to `rpcs3.exe`, so the package is portable:
firmware in `dev_flash/`, saves in `dev_hdd0/home/00000001/savedata/`, patches in
`patches/patch.yml`.

The Unlock FPS patch (v2.1) works with the default Clocks scale and Vblank rate; it caps the
game at 60 FPS. Patches only match the original disc versions (US/EU 01.00, JP/Asia 01.04);
with a game update installed the launcher says so and the game runs at 30 FPS.

## Building

Requirements (from [BUILDING.md](../BUILDING.md)):

- Visual Studio 2022 or 2026 with "Desktop development with C++"
- [Qt 6.12.0](https://www.qt.io/download-qt-installer) for `msvc2022_64`, with the
  Qt Multimedia module; set `Qt6_ROOT` (e.g. `C:\Qt\6.12.0\msvc2022_64`)
- [Vulkan SDK 1.4.341.1](https://vulkan.lunarg.com/sdk/home)
- A Windows [Python 3.10+](https://www.python.org/downloads/windows/) for the launcher

```powershell
git submodule update --init --recursive
# Precompiled LLVM (saves hours): extract into build\lib_ext\Release-x64
#   https://github.com/RPCS3/llvm-mirror/releases/download/custom-build-win-22.1.8/llvmlibs_mt.7z
.\demons_souls\packaging\build.ps1 -Package  # rpcs3.sln Release -> bin\rpcs3.exe -> out\DemonsSouls-windows-x64.zip
```

`scripts\win_build.ps1` (CMake + Ninja, output in `build\bin`) also works, but it compiles
LLVM from source; `package.ps1` finds either output.

Launcher during development, against an RPCS3 build:

```powershell
$env:DES_EMU_DIR = "$PWD\build\bin"
python demons_souls\launcher\des_launcher.py
python -m unittest discover -s demons_souls\launcher\tests
```
