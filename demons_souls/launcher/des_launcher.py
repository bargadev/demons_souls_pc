"""Demon's Souls launcher: pick the game and firmware, set the options, press PLAY.

    des_launcher.py          open the launcher
    des_launcher.py --play   start the game with the saved settings (desktop shortcuts)

Set DES_EMU_DIR to the RPCS3 build folder when running from source.
"""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import des_core
from des_i18n import Translator


class Launcher:
    def __init__(self, root: tk.Tk, emu_dir: Path, tr: Translator):
        self.root = root
        self.emu_dir = emu_dir
        self.tr = tr
        self.settings_path = emu_dir / des_core.SETTINGS_FILE
        self.settings = des_core.Settings.load(self.settings_path)
        self.game: des_core.GameInfo | None = None

        root.title(tr("window_title"))
        root.resizable(False, False)
        icon = emu_dir / "demons_souls.ico"
        if icon.is_file():
            try:
                root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        self.vars = {
            "game_dir": tk.StringVar(value=self.settings.game_dir),
            "fps": tk.IntVar(value=self.settings.fps),
            "resolution": tk.StringVar(value=self.settings.resolution),
            "upscaler": tk.StringVar(value=self.settings.upscaler),
            "sharpening": tk.IntVar(value=self.settings.sharpening),
            "aspect_ratio": tk.StringVar(value=self.settings.aspect_ratio),
            "anisotropic": tk.IntVar(value=self.settings.anisotropic),
            "vsync": tk.BooleanVar(value=self.settings.vsync),
            "fullscreen": tk.BooleanVar(value=self.settings.fullscreen),
            "skip_intro": tk.BooleanVar(value=self.settings.skip_intro),
            "motion_blur": tk.BooleanVar(value=self.settings.motion_blur),
            "perf_overlay": tk.BooleanVar(value=self.settings.perf_overlay),
        }
        self.game_status = tk.StringVar()
        self.firmware_status = tk.StringVar()
        self._build()
        self.refresh_game()
        self.refresh_firmware()

    # --- layout ---------------------------------------------------------------------------

    def _build(self) -> None:
        tr = self.tr
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)

        game = ttk.LabelFrame(frame, text=tr("game"), padding=8)
        game.grid(row=0, column=0, columnspan=2, sticky="ew")
        game.columnconfigure(1, weight=1)
        ttk.Label(game, text=tr("game_folder")).grid(row=0, column=0, sticky="w")
        ttk.Entry(game, textvariable=self.vars["game_dir"], width=48, state="readonly").grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(game, text=tr("browse"), command=self.choose_game).grid(row=0, column=2)
        ttk.Label(game, textvariable=self.game_status, wraplength=520).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Label(game, text=tr("firmware")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(game, textvariable=self.firmware_status, wraplength=380).grid(row=2, column=1, sticky="w", padx=6, pady=(8, 0))
        ttk.Button(game, text=tr("install_firmware"), command=self.install_firmware).grid(row=2, column=2, pady=(8, 0))

        graphics = ttk.LabelFrame(frame, text=tr("graphics"), padding=8)
        graphics.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
        graphics.columnconfigure(1, weight=1)
        row = 0

        def label(text: str) -> None:
            ttk.Label(graphics, text=text).grid(row=row, column=0, sticky="w", pady=2)

        label(tr("fps"))
        fps = ttk.Frame(graphics)
        fps.grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(fps, text=tr("fps_60"), value=60, variable=self.vars["fps"]).pack(side="left")
        ttk.Radiobutton(fps, text=tr("fps_30"), value=30, variable=self.vars["fps"]).pack(side="left", padx=8)
        row += 1

        label(tr("resolution"))
        ttk.Combobox(graphics, textvariable=self.vars["resolution"], values=list(des_core.RESOLUTIONS), state="readonly", width=24).grid(row=row, column=1, sticky="w")
        row += 1

        label(tr("upscaler"))
        self.upscaler_names = {key: tr(f"upscaler_{key}") for key in des_core.UPSCALERS}
        upscaler = ttk.Combobox(graphics, values=list(self.upscaler_names.values()), state="readonly", width=24)
        upscaler.set(self.upscaler_names[self.settings.upscaler])
        upscaler.bind("<<ComboboxSelected>>", lambda _e: self.vars["upscaler"].set(
            next(key for key, name in self.upscaler_names.items() if name == upscaler.get())))
        upscaler.grid(row=row, column=1, sticky="w")
        row += 1

        label(tr("sharpening"))
        ttk.Scale(graphics, from_=0, to=100, variable=self.vars["sharpening"], length=200,
                  command=lambda value: self.vars["sharpening"].set(round(float(value)))).grid(row=row, column=1, sticky="w")
        row += 1

        label(tr("aspect_ratio"))
        ttk.Combobox(graphics, textvariable=self.vars["aspect_ratio"], values=list(des_core.ASPECT_RATIOS), state="readonly", width=24).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(graphics, text=tr("wide_note"), foreground="gray", wraplength=420).grid(row=row, column=1, sticky="w")
        row += 1

        label(tr("anisotropic"))
        self.anisotropic_names = {0: tr("anisotropic_off"), 2: "2x", 4: "4x", 8: "8x", 16: "16x"}
        anisotropic = ttk.Combobox(graphics, values=list(self.anisotropic_names.values()), state="readonly", width=24)
        anisotropic.set(self.anisotropic_names[self.settings.anisotropic])
        anisotropic.bind("<<ComboboxSelected>>", lambda _e: self.vars["anisotropic"].set(
            next(key for key, name in self.anisotropic_names.items() if name == anisotropic.get())))
        anisotropic.grid(row=row, column=1, sticky="w")
        row += 1

        for key in ("vsync", "fullscreen"):
            ttk.Checkbutton(graphics, text=tr(key), variable=self.vars[key]).grid(row=row, column=1, sticky="w")
            row += 1

        options = ttk.LabelFrame(frame, text=tr("game_options"), padding=8)
        options.grid(row=2, column=0, columnspan=2, sticky="ew")
        for index, key in enumerate(("skip_intro", "motion_blur", "perf_overlay")):
            ttk.Checkbutton(options, text=tr(key), variable=self.vars[key]).grid(row=index, column=0, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        buttons.columnconfigure(0, weight=1)
        ttk.Button(buttons, text=tr("advanced"), command=self.open_rpcs3).grid(row=0, column=0, sticky="w")
        play = ttk.Button(buttons, text=tr("play"), command=self.play)
        play.grid(row=0, column=1, sticky="e", ipadx=24, ipady=6)
        play.focus_set()
        self.root.bind("<Return>", lambda _e: self.play())

    # --- state ----------------------------------------------------------------------------

    def collect(self) -> des_core.Settings:
        values = {key: var.get() for key, var in self.vars.items()}
        self.settings = des_core.Settings(**values).normalized()
        return self.settings

    def save(self) -> None:
        try:
            self.collect().save(self.settings_path)
        except OSError:
            pass

    def refresh_game(self) -> None:
        folder = self.vars["game_dir"].get()
        self.game = None
        if not folder:
            self.game_status.set(self.tr("no_game"))
            return
        try:
            self.game = des_core.find_game(folder)
        except (des_core.GameError, OSError) as error:
            self.game_status.set(str(error))
            return
        key = "game_ok" if self.game.patchable else "game_unpatched"
        self.game_status.set(self.tr(key, title=self.game.title, serial=self.game.title_id, version=self.game.app_version))

    def refresh_firmware(self) -> None:
        version = des_core.firmware_version(self.emu_dir)
        self.firmware_status.set(self.tr("firmware_ok", version=version) if version else self.tr("firmware_missing"))

    # --- actions --------------------------------------------------------------------------

    def choose_game(self) -> None:
        folder = filedialog.askdirectory(parent=self.root, initialdir=self.vars["game_dir"].get() or None)
        if folder:
            self.vars["game_dir"].set(folder)
            self.refresh_game()
            self.save()

    def emulator_ok(self) -> bool:
        exe = self.emu_dir / "rpcs3.exe"
        if exe.is_file():
            return True
        messagebox.showerror(self.tr("error"), self.tr("missing_emulator", path=exe), parent=self.root)
        return False

    def install_firmware(self) -> None:
        if not self.emulator_ok():
            return
        pup = filedialog.askopenfilename(parent=self.root, filetypes=[(self.tr("pup_filter"), "*.PUP"), ("*", "*")])
        if not pup:
            return
        process = des_core.launch(des_core.install_firmware_command(self.emu_dir, pup), self.emu_dir)
        messagebox.showinfo(self.tr("firmware"), self.tr("firmware_started"), parent=self.root)
        self._refresh_when_done(process)

    def _refresh_when_done(self, process) -> None:
        if process.poll() is None:
            self.root.after(1000, self._refresh_when_done, process)
        else:
            self.refresh_firmware()

    def open_rpcs3(self) -> None:
        if self.emulator_ok():
            des_core.launch([str(self.emu_dir / "rpcs3.exe")], self.emu_dir)

    def play(self) -> None:
        self.save()
        if not self.emulator_ok():
            return
        if self.game is None:
            messagebox.showerror(self.tr("error"), self.tr("need_game"), parent=self.root)
            return
        if des_core.firmware_version(self.emu_dir) is None:
            messagebox.showerror(self.tr("error"), self.tr("need_firmware"), parent=self.root)
            return
        try:
            des_core.write_rpcs3_files(self.emu_dir, self.settings, self.game)
            des_core.launch(des_core.play_command(self.emu_dir, self.settings, self.game), self.emu_dir)
        except OSError as error:
            messagebox.showerror(self.tr("error"), str(error), parent=self.root)
            return
        self.root.destroy()


def play_saved(emu_dir: Path, tr: Translator) -> bool:
    """Start the game without the window; False when the setup is incomplete."""
    settings = des_core.Settings.load(emu_dir / des_core.SETTINGS_FILE)
    if not (emu_dir / "rpcs3.exe").is_file() or des_core.firmware_version(emu_dir) is None:
        return False
    try:
        game = des_core.find_game(settings.game_dir)
        des_core.write_rpcs3_files(emu_dir, settings, game)
        des_core.launch(des_core.play_command(emu_dir, settings, game), emu_dir)
    except (des_core.GameError, OSError):
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--play", action="store_true", help="start the game with the saved settings")
    parser.add_argument("--lang", choices=["en", "pt"], help="launcher language")
    args = parser.parse_args(argv)

    emu_dir = des_core.emulator_dir()
    tr = Translator(args.lang)
    if args.play and play_saved(emu_dir, tr):
        return 0

    root = tk.Tk()
    Launcher(root, emu_dir, tr)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
