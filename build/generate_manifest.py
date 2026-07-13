"""Генерация manifest.json для релиза."""
import argparse
import hashlib
import json
from pathlib import Path


def sha256sum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_manifest(setup_path: Path, version: str, output: Path):
    manifest = {
        "schemaVersion": 1,
        "product": "rlox-app-tracker",
        "channel": "stable",
        "version": version,
        "minimumLauncherVersion": "1.0.0",
        "publishedAt": "",
        "mandatory": False,
        "installer": {
            "url": f"https://github.com/InVaeR/RLOX-App-Tracker/releases/download/v{version}/{setup_path.name}",
            "sha256": sha256sum(setup_path),
            "size": setup_path.stat().st_size,
        },
        "releaseNotesUrl": f"https://github.com/InVaeR/RLOX-App-Tracker/releases/tag/v{version}",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Манифест записан: {output}")
    print(f"SHA-256: {manifest['installer']['sha256']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("setup", type=Path)
    parser.add_argument("version", type=str)
    parser.add_argument("--output", type=Path, default=Path("release/latest.json"))
    args = parser.parse_args()
    generate_manifest(args.setup, args.version, args.output)
