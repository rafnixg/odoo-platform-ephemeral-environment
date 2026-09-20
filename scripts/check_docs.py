"""Check that the Spanish and English documentation trees stay in sync."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "gh-docs"


def markdown_files(language: str) -> set[Path]:
    language_root = DOCS_ROOT / language
    return {
        path.relative_to(language_root)
        for path in language_root.rglob("*.md")
        if path.is_file()
    }


def main() -> int:
    spanish = markdown_files("es")
    english = markdown_files("en")
    missing_english = sorted(spanish - english)
    missing_spanish = sorted(english - spanish)
    if missing_english or missing_spanish:
        if missing_english:
            print("Missing English pages:")
            for path in missing_english:
                print(f"  {path.as_posix()}")
        if missing_spanish:
            print("Missing Spanish pages:")
            for path in missing_spanish:
                print(f"  {path.as_posix()}")
        return 1
    print(f"Documentation trees match: {len(spanish)} Markdown pages per language")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
