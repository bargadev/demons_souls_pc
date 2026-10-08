"""Game detection, settings and RPCS3 file generation for the Demon's Souls launcher.

Standard library only, so the launcher freezes into a small executable and the tests run
anywhere. The GUI lives in des_launcher.py.
"""

from __future__ import annotations

import dataclasses
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

GAME_TITLE = "Demon's Souls"

# Versions the community patches target: serial -> (PPU hash, app version, title in patch.yml).
# Keep in sync with demons_souls/patches/patch.yml.
PATCH_TARGETS = {
    "BLUS30443": ("PPU-83681f6110d33442329073b72b8dc88a2f677172", "01.00", GAME_TITLE),
    "BLES00932": ("PPU-5446a2645880eefa75f7e374abd6b7818511e2ef", "01.00", GAME_TITLE),
    "BCAS20071": ("PPU-9403fe1678487def5d7f3c380b4c4fb275035378", "01.04", GAME_TITLE),
    "BCJS30022": ("PPU-68544b29e92609ccb2710f485ae7708e4cb35df1", "01.04", GAME_TITLE),
    "BLUD80018": ("PPU-f965a746d844cd0c572a7e8731b5b3b7a81f7bdd", "01.01", "Demon's Souls Trade Demo"),
}

# Other releases are recognised by their PARAM.SFO title.
TITLE_MARKERS = ("demon's souls", "demons souls", "デモンズソウル")

# Value of the "Aspect Ratio" patch for each choice; None means the native 16:9.
ASPECT_RATIOS = {
    "16:9": None,
    "16:10": 1.6,
    "21:9 (2560x1080)": 2.37037037037037,
    "21:9 (3440x1440)": 2.388888888888889,
    "21:9 (3840x1600)": 2.4,
    "32:9": 3.555555555555556,
}

# HUD/menu centering patches for wide screens; only the US version has them.
HUD_PATCHES = {
    "21:9 (2560x1080)": "Aspect ratio (HUD/Menus) 21:9 (2560x1080)",
    "21:9 (3440x1440)": "Aspect ratio (HUD/Menus) 21:9 (3440x1440)",
    "21:9 (3840x1600)": "Aspect ratio (HUD/Menus) 21:9 (3840x1600)",
    "32:9": "Aspect ratio (HUD/Menus) 32:9",
}

# Resolution scale (percent of the native 1280x720) for each output choice.
RESOLUTIONS = {
    "720p": 100,
    "1080p": 150,
    "1440p": 200,
    "4K": 300,
}

UPSCALERS = {
    "bilinear": "Bilinear",
    "fsr": "FidelityFX Super Resolution",
}

SETTINGS_FILE = "launcher_settings.json"
CONFIG_FILE = "demons_souls_config.yml"


class GameError(Exception):
    """The chosen folder is not a usable Demon's Souls dump."""


@dataclasses.dataclass
class GameInfo:
    title_id: str
    app_version: str
    title: str
    eboot: Path

    @property
    def patchable(self) -> bool:
        target = PATCH_TARGETS.get(self.title_id)
        return target is not None and target[1] == self.app_version


@dataclasses.dataclass
class Settings:
    game_dir: str = ""
    fps: int = 60
    resolution: str = "1080p"
    upscaler: str = "fsr"
    sharpening: int = 50
    aspect_ratio: str = "16:9"
    vsync: bool = True
    fullscreen: bool = True
    skip_intro: bool = True
    motion_blur: bool = True
    anisotropic: int = 16
    perf_overlay: bool = False

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        names = {field.name for field in dataclasses.fields(cls)}
        settings = cls(**{key: value for key, value in data.items() if key in names})
        return settings.normalized()

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(dataclasses.asdict(self), indent=2), encoding="utf-8")

    def normalized(self) -> "Settings":
        """Replace values a hand-edited or older settings file may have broken."""
        default = Settings()
        if self.fps not in (30, 60):
            self.fps = default.fps
        if self.resolution not in RESOLUTIONS:
            self.resolution = default.resolution
        if self.upscaler not in UPSCALERS:
            self.upscaler = default.upscaler
        if self.aspect_ratio not in ASPECT_RATIOS:
            self.aspect_ratio = default.aspect_ratio
        if self.anisotropic not in (0, 2, 4, 8, 16):
            self.anisotropic = default.anisotropic
        try:
            self.sharpening = max(0, min(100, int(self.sharpening)))
        except (TypeError, ValueError):
            self.sharpening = default.sharpening
        return self


# --- PARAM.SFO -----------------------------------------------------------------------------

def parse_sfo(data: bytes) -> dict[str, object]:
    """Read a PARAM.SFO file into a dict of its keys (strings and integers)."""
    if len(data) < 20 or data[:4] != b"\0PSF":
        raise GameError("PARAM.SFO is not valid")
    key_table, data_table, count = struct.unpack_from("<III", data, 8)
    entries: dict[str, object] = {}
    for index in range(count):
        offset = 20 + index * 16
        if offset + 16 > len(data):
            raise GameError("PARAM.SFO is truncated")
        key_offset, fmt, length, _max_length, data_offset = struct.unpack_from("<HHIII", data, offset)
        key_start = key_table + key_offset
        key_end = data.index(b"\0", key_start)
        key = data[key_start:key_end].decode("utf-8", "replace")
        value_start = data_table + data_offset
        raw = data[value_start:value_start + length]
        if fmt == 0x0404:
            entries[key] = struct.unpack("<I", raw[:4])[0] if len(raw) >= 4 else 0
        else:
            entries[key] = raw.split(b"\0", 1)[0].decode("utf-8", "replace")
    return entries


def find_game(path: str | os.PathLike[str]) -> GameInfo:
    """Find the game from a folder the player picked: the dump root, PS3_GAME, USRDIR, or EBOOT.BIN."""
    picked = Path(path)
    if picked.is_file():
        picked = picked.parent
    candidates = [picked, picked / "PS3_GAME", picked.parent, picked.parent.parent]
    for folder in candidates:
        sfo = folder / "PARAM.SFO"
        eboot = folder / "USRDIR" / "EBOOT.BIN"
        if sfo.is_file() and eboot.is_file():
            break
    else:
        raise GameError("No PS3_GAME/PARAM.SFO and USRDIR/EBOOT.BIN found in this folder")

    entries = parse_sfo(sfo.read_bytes())
    title_id = str(entries.get("TITLE_ID", ""))
    title = str(entries.get("TITLE", ""))
    if title_id not in PATCH_TARGETS and not any(marker in title.lower() for marker in TITLE_MARKERS):
        raise GameError(f"{title or title_id or 'This game'} is not Demon's Souls")
    return GameInfo(
        title_id=title_id,
        app_version=str(entries.get("APP_VER", "")),
        title=title or GAME_TITLE,
        eboot=eboot,
    )


# --- YAML output ---------------------------------------------------------------------------

def _scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value), ensure_ascii=False)


def to_yaml(tree: dict, indent: int = 0) -> str:
    """Write nested dicts of scalars as block YAML; every key and string is quoted."""
    lines = []
    for key, value in tree.items():
        prefix = " " * indent + json.dumps(str(key), ensure_ascii=False) + ":"
        if isinstance(value, dict):
            lines.append(prefix)
            lines.append(to_yaml(value, indent + 2))
        else:
            lines.append(f"{prefix} {_scalar(value)}")
    return "\n".join(line for line in lines if line)


# --- RPCS3 files ---------------------------------------------------------------------------

def build_config(settings: Settings) -> dict:
    """Config override passed with --config. RPCS3 applies it over its defaults."""
    wide = ASPECT_RATIOS[settings.aspect_ratio] is not None
    return {
        "Core": {
            "PPU Decoder": "Recompiler (LLVM)",
            "SPU Decoder": "Recompiler (LLVM)",
        },
        "Video": {
            "Renderer": "Vulkan",
            "Resolution": "1280x720",
            "Aspect ratio": "16:9",
            "Frame limit": "Auto",
            "VSync Mode": "Full" if settings.vsync else "Disabled",
            "Stretch To Display Area": wide,
            "Resolution Scale": RESOLUTIONS[settings.resolution],
            "Anisotropic Filter Override": settings.anisotropic,
            "Output Scaling Mode": UPSCALERS[settings.upscaler],
            "FidelityFX CAS Sharpening Intensity": settings.sharpening,
            "Performance Overlay": {
                "Enabled": settings.perf_overlay,
            },
        },
        "Miscellaneous": {
            "Exit RPCS3 when process finishes": True,
            "Start games in fullscreen mode": settings.fullscreen,
            "Show trophy popups": False,
            "Show shader compilation hint": True,
        },
    }


def enabled_patches(settings: Settings, game: GameInfo) -> dict[str, dict]:
    """Patch description -> config entry for the patches this setup turns on."""
    patches: dict[str, dict] = {}
    if settings.fps == 60:
        patches["Unlock FPS"] = {"Enabled": True}
    if settings.skip_intro:
        patches["Skip Intro Videos"] = {"Enabled": True}
    if not settings.motion_blur:
        patches["Disable Motion Blur"] = {"Enabled": True}
    ratio = ASPECT_RATIOS[settings.aspect_ratio]
    if ratio is not None:
        patches["Aspect Ratio"] = {"Enabled": True, "Configurable Values": {"Aspect Ratio": ratio}}
        hud = HUD_PATCHES.get(settings.aspect_ratio)
        if hud and game.title_id == "BLUS30443":
            patches[hud] = {"Enabled": True}
    return patches


def build_patch_config(settings: Settings, game: GameInfo) -> dict:
    """patch_config.yml: hash -> patch -> title -> serial -> version -> values."""
    if not game.patchable:
        return {}
    ppu_hash, version, title = PATCH_TARGETS[game.title_id]
    return {
        ppu_hash: {
            description: {title: {game.title_id: {version: values}}}
            for description, values in enabled_patches(settings, game).items()
        }
    }


def firmware_version(emu_dir: Path) -> str | None:
    """Installed PS3 firmware version, or None when it still has to be installed."""
    version_file = emu_dir / "dev_flash" / "vsh" / "etc" / "version.txt"
    try:
        text = version_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # Same reading as utils::get_firmware_version: "release:04.9200:build:..." -> "4.92"
    fields = text.split(":")
    if len(fields) < 3:
        return "?"
    version = fields[1].strip().lstrip("0")
    if "." in version:
        major, minor = version.split(".", 1)
        version = f"{major}.{minor.rstrip('0') or '0'}"
    return version or "?"


def config_dir(emu_dir: Path) -> Path:
    """RPCS3 on Windows keeps its settings, patch_config.yml included, in <exe dir>/config/."""
    return emu_dir / "config"


def write_rpcs3_files(emu_dir: Path, settings: Settings, game: GameInfo) -> Path:
    """Write the config override and patch_config.yml; returns the config path."""
    folder = config_dir(emu_dir)
    folder.mkdir(parents=True, exist_ok=True)
    config_path = folder / CONFIG_FILE
    config_path.write_text(to_yaml(build_config(settings)) + "\n", encoding="utf-8")
    (folder / "patch_config.yml").write_text(to_yaml(build_patch_config(settings, game)) + "\n", encoding="utf-8")
    return config_path


def play_command(emu_dir: Path, settings: Settings, game: GameInfo) -> list[str]:
    command = [str(emu_dir / "rpcs3.exe"), "--no-gui"]
    if settings.fullscreen:
        command.append("--fullscreen")
    command += ["--config", str(config_dir(emu_dir) / CONFIG_FILE), str(game.eboot)]
    return command


def install_firmware_command(emu_dir: Path, pup: str) -> list[str]:
    return [str(emu_dir / "rpcs3.exe"), "--installfw", pup]


def emulator_dir() -> Path:
    """Folder holding rpcs3.exe: next to the frozen launcher, or DES_EMU_DIR for development."""
    override = os.environ.get("DES_EMU_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def launch(command: list[str], cwd: Path) -> subprocess.Popen:
    return subprocess.Popen(command, cwd=str(cwd))
