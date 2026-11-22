"""Download the corpus PDFs listed in data/sources.toml into data/raw/.

Records a SHA-256 per file in data/checksums.json (committed), so a later run can tell
when Arduino has revised a datasheet. Polite: one request per second, existing files skipped.

    uv run python scripts/download.py            # download missing files, verify the rest
    uv run python scripts/download.py --update   # accept changed checksums
"""

import argparse
import hashlib
import json
import sys
import time
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.toml"
RAW = ROOT / "data" / "raw"
MD = ROOT / "data" / "source_md"  # CC BY-SA markdown originals, used to verify the golden set
CHECKSUMS = ROOT / "data" / "checksums.json"
USER_AGENT = "datasheet-support-agent/0.1 (open-source research demo)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        if "pdf" not in resp.headers.get("Content-Type", ""):
            raise RuntimeError(f"{url} did not return a PDF")
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"{url} is not a PDF file")
    dest.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="accept changed checksums")
    args = ap.parse_args()

    cfg = tomllib.loads(SOURCES.read_text())
    known = json.loads(CHECKSUMS.read_text()) if CHECKSUMS.exists() else {}
    RAW.mkdir(parents=True, exist_ok=True)
    problems = 0

    for ds in cfg["datasheet"]:
        sku = ds["sku"]
        dest = RAW / f"{sku}.pdf"
        if not dest.exists():
            url = cfg["url_template"].format(sku=sku)
            print(f"download {sku} {url}")
            fetch(url, dest)
            time.sleep(1)
        digest = sha256(dest)
        if sku in known and known[sku]["sha256"] != digest and not args.update:
            print(
                f"CHANGED  {sku}: checksum differs from data/checksums.json (rerun with --update)"
            )
            problems += 1
            continue
        known[sku] = {"product": ds["product"], "sha256": digest, "bytes": dest.stat().st_size}

    # Markdown originals at the pinned commit (independent check for scripts/build_golden.py).
    MD.mkdir(parents=True, exist_ok=True)
    for ds in cfg["datasheet"]:
        dest = MD / f"{ds['sku']}.md"
        if not dest.exists():
            url = (
                f"https://raw.githubusercontent.com/arduino/docs-content/"
                f"{cfg['source_commit']}/{ds['source_md']}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())

    CHECKSUMS.write_text(json.dumps(dict(sorted(known.items())), indent=2) + "\n")
    print(f"{len(cfg['datasheet'])} datasheets, {problems} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
