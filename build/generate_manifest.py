import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


VERSION_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

VALID_CHANNELS = {"stable", "beta", "dev"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", required=True, choices=sorted(VALID_CHANNELS))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-launcher-version", default="2.0.0")
    args = parser.parse_args()

    setup = args.setup.resolve()

    if not setup.is_file():
        raise SystemExit(f"Setup file does not exist: {setup}")

    if not VERSION_PATTERN.fullmatch(args.version):
        raise SystemExit(f"Invalid SemVer: {args.version}")

    if not VERSION_PATTERN.fullmatch(args.minimum_launcher_version):
        raise SystemExit(
            "Invalid minimum launcher version: "
            f"{args.minimum_launcher_version}"
        )

    if "/" not in args.repository:
        raise SystemExit(f"Invalid GitHub repository: {args.repository}")

    tag = f"v{args.version}"
    encoded_name = quote(setup.name)

    installer_url = (
        f"https://github.com/{args.repository}/releases/download/"
        f"{tag}/{encoded_name}"
    )

    release_url = (
        f"https://github.com/{args.repository}/releases/tag/{tag}"
    )

    manifest = {
        "schemaVersion": 1,
        "product": "rlox-app-tracker",
        "channel": args.channel,
        "version": args.version,
        "minimumLauncherVersion": args.minimum_launcher_version,
        "publishedAt": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "mandatory": False,
        "installer": {
            "url": installer_url,
            "sha256": sha256_file(setup),
            "size": setup.stat().st_size,
        },
        "releaseNotesUrl": release_url,
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    temp.replace(output)

    print(f"Manifest written to: {output}")
    print(f"Installer: {setup}")
    print(f"Version: {args.version}")
    print(f"Channel: {args.channel}")
    print(f"SHA-256: {manifest['installer']['sha256']}")
    print(f"Size: {manifest['installer']['size']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
