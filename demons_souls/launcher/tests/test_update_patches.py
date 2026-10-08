import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import update_patches  # noqa: E402

DATABASE = """Version: 1.2

Anchors:
  BLUS30443_FpsUnlock: &BLUS30443_FpsUnlock
    - [ be16, 0x00025ed8, 0x981f ]

PPU-83681f6110d33442329073b72b8dc88a2f677172:
  "Unlock FPS":
    Games:
      "Demon's Souls":
        BLUS30443: [ 01.00 ]

Anchors:
  other: &other

PPU-d626d9832ed48d1ff0d8d97e53a4e23df50cfae6:
  "21:9 Aspect Ratio":
    Games:
      "Kingdom Hearts HD 1.5 ReMIX":
        BLUS31212: [ All ]
"""


class ExtractTest(unittest.TestCase):
    def test_keeps_only_demons_souls(self):
        text = update_patches.extract(DATABASE)
        self.assertTrue(text.startswith("# Demon's Souls"))
        self.assertIn("Version: 1.2\n\nAnchors:\n", text)
        self.assertIn("PPU-83681f6110d33442329073b72b8dc88a2f677172:", text)
        self.assertNotIn("Kingdom Hearts", text)

    def test_rejects_unexpected_input(self):
        with self.assertRaises(ValueError):
            update_patches.extract("<html>")
        with self.assertRaises(ValueError):
            update_patches.extract("Version: 1.2\nAnchors:\n  x: 1\n")

    def test_shipped_file_is_current_format(self):
        shipped = update_patches.OUT.read_text(encoding="utf-8")
        self.assertIn("\nVersion: 1.2\n", shipped)
        self.assertEqual(shipped.count("\nPPU-"), 5)


if __name__ == "__main__":
    unittest.main()
