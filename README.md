# Demon's Souls for Windows

**Work in progress.** A single-game build of [RPCS3](https://github.com/RPCS3/rpcs3) focused on
Demon's Souls (PS3): boots straight into the game, ships with the right settings and community
patches, and gets its own launcher, in the spirit of
[bloodborne_pc](https://github.com/bargadev/bloodborne_pc).

> **No game files or PS3 firmware are included.** You need your own disc dump of Demon's Souls
> (BLUS30443 US or BLES00932 EU; PSN versions are not supported) and the official
> `PS3UPDAT.PUP` firmware.
> This project is not affiliated with Sony Interactive Entertainment, FromSoftware or the
> RPCS3 team.

## Why not a "native" port like Bloodborne?

The PS4 has an x86-64 CPU, so Bloodborne's own code runs directly on a PC. The PS3 uses the
Cell processor (a big-endian PowerPC core plus six SPUs) and the RSX GPU, so every instruction
has to be translated. RPCS3 already does this well (LLVM recompilers for PPU and SPU), so this
project builds on it instead of starting over.

## Roadmap

1. **Build on Windows** from this fork (MSYS2/clang or Visual Studio 2022 + Qt 6).
2. **Single-game mode:** the executable boots the Demon's Souls `EBOOT.BIN` directly, with no
   game list and no emulator UI.
3. **Preset configuration:** tuned PPU/SPU/RSX settings, resolution scaling, and the 60 FPS
   patch enabled out of the box. *(done: launcher writes a config override and
   `patch_config.yml`)*
4. **Launcher:** choose the game folder, install the firmware, FPS 30/60, output resolution,
   FSR 1 + sharpening, aspect ratio (21:9, 32:9), skip intro, motion blur. *(done, English and
   Portuguese)*
5. **Fixes and extras:** physics above 60 FPS, community online server support, controller
   setup inside the launcher.
6. **Packaging:** one zip with the game executable and launcher; firmware and game supplied by
   the user. *(script done: `demons_souls/packaging/package.ps1`)*

Details, layout and build steps: [demons_souls/README.md](demons_souls/README.md).

## How to play (once a release is out)

1. Unpack the zip and start `Demons Souls.exe`.
2. Choose your game folder (the one with `PS3_GAME`).
3. **Install firmware...** and pick `PS3UPDAT.PUP`.
4. Press **PLAY**.

Do not install game updates: the patches match the original disc versions only.

## Branches

- `demons_souls`: project work.
- `master`: tracks upstream RPCS3 (`upstream` remote) for merges.

## Credits

Built on [RPCS3](https://github.com/RPCS3/rpcs3) by the RPCS3 team. The original README is in
[docs/original-readme](docs/original-readme/README.md). 60 FPS patch by Whatcookie.

## License

GNU GPL v2 ([LICENSE](LICENSE)), same as RPCS3. Third-party components keep their own
licenses.
