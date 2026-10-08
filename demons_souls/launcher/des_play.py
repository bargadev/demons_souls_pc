"""`Play Demons Souls.exe`: start the game with the saved settings, or open the launcher
when the setup is not finished yet."""

import sys

import des_launcher

if __name__ == "__main__":
    sys.exit(des_launcher.main(["--play", *sys.argv[1:]]))
