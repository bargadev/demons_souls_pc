"""Refresh demons_souls/patches/patch.yml from the RPCS3 patch database.

The database is one file with a section per game, each starting with a top-level
"Anchors:" key. This keeps the sections that mention a Demon's Souls serial.

    python demons_souls/tools/update_patches.py
"""

import json
import sys
import urllib.request
from pathlib import Path

API = "https://rpcs3.net/compatibility?patch&api=v1&v=1.2"
SERIALS = ("BLUS30443", "BLES00932", "BCAS20071", "BCJS30022", "BLUD80018")
OUT = Path(__file__).resolve().parent.parent / "patches" / "patch.yml"
HEADER = (
    "# Demon's Souls section of the RPCS3 patch database (https://rpcs3.net/compatibility?patch).\n"
    "# Authors are credited per patch. Refresh with demons_souls/tools/update_patches.py.\n"
)


def extract(database: str) -> str:
    lines = database.splitlines()
    if not lines or not lines[0].startswith("Version:"):
        raise ValueError("unexpected patch database format")
    sections: list[list[str]] = []
    for line in lines[1:]:
        if line.startswith("Anchors:") or not sections:
            sections.append([])
        sections[-1].append(line.rstrip())
    kept = [section for section in sections if any(serial in "\n".join(section) for serial in SERIALS)]
    if not kept:
        raise ValueError("no Demon's Souls patches found")
    body = "\n".join("\n".join(section).strip("\n") for section in kept)
    return f"{HEADER}{lines[0]}\n\n{body}\n"


def main() -> int:
    request = urllib.request.Request(API, headers={"User-Agent": "demons_souls_pc"})
    with urllib.request.urlopen(request, timeout=60) as response:
        reply = json.load(response)
    if reply.get("return_code") != 0:
        print(f"patch server returned {reply.get('return_code')}", file=sys.stderr)
        return 1
    OUT.write_text(extract(reply["patch"]), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
