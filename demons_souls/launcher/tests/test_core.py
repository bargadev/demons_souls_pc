import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import des_core  # noqa: E402

PATCH_DB = Path(__file__).resolve().parents[2] / "patches" / "patch.yml"


def make_sfo(entries: dict) -> bytes:
    """Build a PARAM.SFO with utf-8 strings and u32 integers."""
    keys = b""
    values = b""
    index = b""
    for key, value in entries.items():
        if isinstance(value, int):
            raw, fmt = struct.pack("<I", value), 0x0404
        else:
            raw, fmt = value.encode() + b"\0", 0x0204
        index += struct.pack("<HHIII", len(keys), fmt, len(raw), len(raw), len(values))
        keys += key.encode() + b"\0"
        values += raw
    key_table = 20 + len(index)
    data_table = key_table + len(keys)
    header = b"\0PSF" + struct.pack("<IIII", 0x0101, key_table, data_table, len(entries))
    return header + index + keys + values


def make_dump(root: Path, title_id="BLUS30443", app_ver="01.00", title="Demon's Souls") -> Path:
    game = root / "PS3_GAME"
    (game / "USRDIR").mkdir(parents=True)
    (game / "USRDIR" / "EBOOT.BIN").write_bytes(b"SCE\0")
    (game / "PARAM.SFO").write_bytes(make_sfo({"APP_VER": app_ver, "PARENTAL_LEVEL": 5, "TITLE": title, "TITLE_ID": title_id}))
    return game


class SfoTest(unittest.TestCase):
    def test_parses_strings_and_integers(self):
        entries = des_core.parse_sfo(make_sfo({"TITLE_ID": "BLES00932", "PARENTAL_LEVEL": 5}))
        self.assertEqual(entries, {"TITLE_ID": "BLES00932", "PARENTAL_LEVEL": 5})

    def test_rejects_garbage(self):
        with self.assertRaises(des_core.GameError):
            des_core.parse_sfo(b"not an sfo file at all")


class FindGameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_accepts_every_folder_level(self):
        game = make_dump(self.root)
        for picked in (self.root, game, game / "USRDIR", game / "USRDIR" / "EBOOT.BIN"):
            info = des_core.find_game(picked)
            self.assertEqual(info.title_id, "BLUS30443")
            self.assertEqual(info.eboot, game / "USRDIR" / "EBOOT.BIN")
            self.assertTrue(info.patchable)

    def test_other_release_found_by_title(self):
        make_dump(self.root, title_id="NPUB30910", title="Demon's Souls™")
        info = des_core.find_game(self.root)
        self.assertFalse(info.patchable)

    def test_updated_disc_is_not_patchable(self):
        make_dump(self.root, app_ver="01.01")
        self.assertFalse(des_core.find_game(self.root).patchable)

    def test_rejects_other_games(self):
        make_dump(self.root, title_id="BLUS30187", title="Dark Souls")
        with self.assertRaises(des_core.GameError):
            des_core.find_game(self.root)

    def test_rejects_empty_folder(self):
        with self.assertRaises(des_core.GameError):
            des_core.find_game(self.root)


class SettingsTest(unittest.TestCase):
    def test_round_trip_and_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / des_core.SETTINGS_FILE
            des_core.Settings(fps=30, resolution="4K", aspect_ratio="32:9").save(path)
            loaded = des_core.Settings.load(path)
            self.assertEqual((loaded.fps, loaded.resolution, loaded.aspect_ratio), (30, "4K", "32:9"))

            path.write_text('{"fps": 144, "resolution": "8K", "sharpening": "x", "unknown": 1}')
            repaired = des_core.Settings.load(path)
            self.assertEqual((repaired.fps, repaired.resolution, repaired.sharpening), (60, "1080p", 50))

            path.write_text("not json")
            self.assertEqual(des_core.Settings.load(path), des_core.Settings())


class GeneratedFilesTest(unittest.TestCase):
    us = des_core.GameInfo("BLUS30443", "01.00", "Demon's Souls", Path("EBOOT.BIN"))
    eu = des_core.GameInfo("BLES00932", "01.00", "Demon's Souls", Path("EBOOT.BIN"))

    def test_patch_targets_exist_in_patch_database(self):
        database = PATCH_DB.read_text(encoding="utf-8")
        for serial, (ppu_hash, version, title) in des_core.PATCH_TARGETS.items():
            self.assertIn(f"{ppu_hash}:", database)
            self.assertIn(serial, database)
        for description in ("Unlock FPS", "Skip Intro Videos", "Disable Motion Blur", "Aspect Ratio", *des_core.HUD_PATCHES.values()):
            self.assertIn(f'"{description}":', database)
        for value in des_core.ASPECT_RATIOS.values():
            if value is not None:
                self.assertIn(repr(value).rstrip("0"), database)

    def test_default_patch_config(self):
        config = des_core.build_patch_config(des_core.Settings(), self.us)
        patches = config["PPU-83681f6110d33442329073b72b8dc88a2f677172"]
        self.assertEqual(set(patches), {"Unlock FPS", "Skip Intro Videos"})
        self.assertEqual(patches["Unlock FPS"], {"Demon's Souls": {"BLUS30443": {"01.00": {"Enabled": True}}}})

    def test_wide_screen_patches(self):
        settings = des_core.Settings(fps=30, skip_intro=False, motion_blur=False, aspect_ratio="21:9 (2560x1080)")
        us = des_core.enabled_patches(settings, self.us)
        self.assertEqual(set(us), {"Disable Motion Blur", "Aspect Ratio", "Aspect ratio (HUD/Menus) 21:9 (2560x1080)"})
        self.assertEqual(us["Aspect Ratio"]["Configurable Values"], {"Aspect Ratio": 2.37037037037037})
        self.assertNotIn("Aspect ratio (HUD/Menus) 21:9 (2560x1080)", des_core.enabled_patches(settings, self.eu))
        self.assertTrue(des_core.build_config(settings)["Video"]["Stretch To Display Area"])

    def test_unpatchable_game_gets_no_patches(self):
        game = des_core.GameInfo("BLUS30443", "01.01", "Demon's Souls", Path("EBOOT.BIN"))
        self.assertEqual(des_core.build_patch_config(des_core.Settings(), game), {})

    def test_config_values(self):
        video = des_core.build_config(des_core.Settings(resolution="4K", upscaler="bilinear", vsync=False))["Video"]
        self.assertEqual(video["Resolution Scale"], 300)
        self.assertEqual(video["Output Scaling Mode"], "Bilinear")
        self.assertEqual(video["VSync Mode"], "Disabled")
        self.assertFalse(video["Stretch To Display Area"])

    def test_yaml_output(self):
        text = des_core.to_yaml({"Video": {"Resolution Scale": 150, "Stretch": False, "Mode": "Full"}, "Demon's": {"x": 2.4}})
        self.assertEqual(text, '"Video":\n  "Resolution Scale": 150\n  "Stretch": false\n  "Mode": "Full"\n"Demon\'s":\n  "x": 2.4')
        self.assertEqual(des_core.to_yaml({}), "")

    def test_write_files_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            emu = Path(tmp)
            config = des_core.write_rpcs3_files(emu, des_core.Settings(), self.us)
            self.assertIn('"Resolution Scale": 150', config.read_text(encoding="utf-8"))
            self.assertEqual(config.parent, emu / "config")
            self.assertIn('"Unlock FPS":', (emu / "config" / "patch_config.yml").read_text(encoding="utf-8"))
            command = des_core.play_command(emu, des_core.Settings(fullscreen=False), self.us)
            self.assertEqual(command[1:], ["--no-gui", "--config", str(config), "EBOOT.BIN"])


class FirmwareTest(unittest.TestCase):
    def test_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            emu = Path(tmp)
            self.assertIsNone(des_core.firmware_version(emu))
            etc = emu / "dev_flash" / "vsh" / "etc"
            etc.mkdir(parents=True)
            (etc / "version.txt").write_text("release:04.9200:build:XXXX\n")
            self.assertEqual(des_core.firmware_version(emu), "4.92")
            (etc / "version.txt").write_text("damaged")
            self.assertEqual(des_core.firmware_version(emu), "?")


if __name__ == "__main__":
    unittest.main()
