"""Verify that a built wheel contains every runtime resource and entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile

REQUIRED_SUFFIXES = {
    "mini_runbot/resources/config.example.yaml",
    "mini_runbot/templates/compose.yaml.j2",
    "mini_runbot/web/app.js",
    "mini_runbot/web/index.html",
    "mini_runbot/web/styles.css",
}


def main() -> int:
    distribution_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    wheels = sorted(distribution_dir.glob("*.whl"))
    source_archives = sorted(distribution_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(source_archives) != 1:
        print("Expected exactly one wheel and one source archive", file=sys.stderr)
        return 1

    with ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        missing = sorted(REQUIRED_SUFFIXES - names)
        entry_points = next(
            (name for name in names if name.endswith(".dist-info/entry_points.txt")), None
        )
        if missing:
            print(f"Wheel is missing runtime resources: {', '.join(missing)}", file=sys.stderr)
            return 1
        if entry_points is None:
            print("Wheel is missing entry_points.txt", file=sys.stderr)
            return 1
        content = wheel.read(entry_points).decode("utf-8")
        if "mini-runbot = mini_runbot.cli.main:app" not in content:
            print("Wheel is missing the mini-runbot console entry point", file=sys.stderr)
            return 1

    print(f"Distribution verified: {wheels[0].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
