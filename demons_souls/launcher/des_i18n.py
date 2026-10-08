"""Launcher strings. English is the fallback for missing keys and languages."""

import locale

STRINGS = {
    "en": {
        "window_title": "Demon's Souls",
        "game": "Game",
        "game_folder": "Game folder",
        "browse": "Browse...",
        "no_game": "Choose the folder of your Demon's Souls disc dump.",
        "game_ok": "{title} ({serial}, version {version})",
        "game_unpatched": "{title} ({serial}, version {version}): patches only work on the disc versions without updates, the game runs at 30 FPS.",
        "firmware": "PS3 firmware",
        "firmware_ok": "Installed ({version})",
        "firmware_missing": "Not installed. Download PS3UPDAT.PUP from PlayStation's site and install it.",
        "install_firmware": "Install firmware...",
        "graphics": "Graphics",
        "fps": "Frame rate",
        "fps_30": "30 FPS (original)",
        "fps_60": "60 FPS",
        "resolution": "Resolution",
        "upscaler": "Upscaling filter",
        "upscaler_bilinear": "Bilinear",
        "upscaler_fsr": "AMD FSR 1",
        "sharpening": "Sharpening (FSR)",
        "aspect_ratio": "Aspect ratio",
        "anisotropic": "Anisotropic filtering",
        "anisotropic_off": "Game default",
        "vsync": "VSync",
        "fullscreen": "Fullscreen",
        "game_options": "Game",
        "skip_intro": "Skip intro videos",
        "motion_blur": "Motion blur",
        "perf_overlay": "Show FPS and performance overlay",
        "play": "PLAY",
        "advanced": "Controls and advanced settings (RPCS3)",
        "error": "Error",
        "missing_emulator": "rpcs3.exe was not found next to the launcher:\n{path}",
        "need_game": "Choose your game folder first.",
        "need_firmware": "Install the PS3 firmware first.",
        "pup_filter": "PS3 firmware",
        "firmware_started": "The firmware installer is running. Close the RPCS3 window when it finishes.",
        "wide_note": "Wide aspect ratios stretch the HUD (the US version can keep it centered).",
    },
    "pt": {
        "window_title": "Demon's Souls",
        "game": "Jogo",
        "game_folder": "Pasta do jogo",
        "browse": "Procurar...",
        "no_game": "Escolha a pasta do dump do disco de Demon's Souls.",
        "game_ok": "{title} ({serial}, versão {version})",
        "game_unpatched": "{title} ({serial}, versão {version}): os patches só funcionam nas versões de disco sem atualização; o jogo roda a 30 FPS.",
        "firmware": "Firmware do PS3",
        "firmware_ok": "Instalado ({version})",
        "firmware_missing": "Não instalado. Baixe o PS3UPDAT.PUP no site da PlayStation e instale.",
        "install_firmware": "Instalar firmware...",
        "graphics": "Gráficos",
        "fps": "Taxa de quadros",
        "fps_30": "30 FPS (original)",
        "fps_60": "60 FPS",
        "resolution": "Resolução",
        "upscaler": "Filtro de escala",
        "upscaler_bilinear": "Bilinear",
        "upscaler_fsr": "AMD FSR 1",
        "sharpening": "Nitidez (FSR)",
        "aspect_ratio": "Proporção da tela",
        "anisotropic": "Filtro anisotrópico",
        "anisotropic_off": "Padrão do jogo",
        "vsync": "VSync",
        "fullscreen": "Tela cheia",
        "game_options": "Jogo",
        "skip_intro": "Pular vídeos de abertura",
        "motion_blur": "Desfoque de movimento",
        "perf_overlay": "Mostrar FPS e desempenho",
        "play": "JOGAR",
        "advanced": "Controles e configurações avançadas (RPCS3)",
        "error": "Erro",
        "missing_emulator": "rpcs3.exe não foi encontrado ao lado do launcher:\n{path}",
        "need_game": "Escolha a pasta do jogo primeiro.",
        "need_firmware": "Instale o firmware do PS3 primeiro.",
        "pup_filter": "Firmware do PS3",
        "firmware_started": "O instalador do firmware está rodando. Feche a janela do RPCS3 quando terminar.",
        "wide_note": "Proporções largas esticam o HUD (a versão americana consegue mantê-lo centralizado).",
    },
}


def system_language() -> str:
    try:
        name = locale.getlocale()[0] or ""
    except ValueError:
        name = ""
    name = name.lower()
    if name.startswith("pt") or name.startswith("portuguese"):
        return "pt"
    return "en"


class Translator:
    def __init__(self, language: str | None = None):
        self.language = language if language in STRINGS else system_language()

    def __call__(self, key: str, **values) -> str:
        text = STRINGS[self.language].get(key) or STRINGS["en"][key]
        return text.format(**values) if values else text
