#!/usr/bin/env python3
"""Downloads one file that the build pins, and checks it against the sha256 the repo records.

What Nova downloads (the Limine release and QEMU's firmware) goes into the build's cache, which
`make clean` keeps, so the network is only needed the first time. The hash is of the bytes as
downloaded. A .bz2 download can be unpacked on the way, with --bunzip2. Nothing is written unless
the hash matches, and the output appears all at once, so an interrupted download leaves nothing
behind that looks finished.

    fetch.py --url URL --sha256 HEX --output FILE [--bunzip2]
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT_SECONDS = 60
USER_AGENT = "nova-build"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def write_atomically(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True, help="the hash of the file as downloaded")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bunzip2", action="store_true", help="unpack the download with bz2")
    args = parser.parse_args(argv)

    try:
        data = download(args.url)
    except (urllib.error.URLError, OSError) as error:
        print(f"fetch: error: couldn't download {args.url}: {error}", file=sys.stderr)
        return 1

    found = hashlib.sha256(data).hexdigest()
    if found != args.sha256.lower():
        print(
            f"fetch: error: {args.url} has sha256 {found}, but the build expects {args.sha256}, "
            f"so it wasn't used",
            file=sys.stderr,
        )
        return 1

    if args.bunzip2:
        data = bz2.decompress(data)
    write_atomically(args.output, data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
