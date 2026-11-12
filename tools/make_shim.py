#!/usr/bin/env python3
"""Makes the header shim: the nine headers that C17 guarantees a freestanding program.

The build compiles with -nostdinc, so that no hosted header is ever visible. The shim is a
directory that holds only the compiler's own copies of the nine freestanding headers, and the
private headers that those include, so that they and nothing else are on the include path.

    make_shim.py --cc CLANG --output DIR
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

FREESTANDING = (
    "float.h",
    "iso646.h",
    "limits.h",
    "stdalign.h",
    "stdarg.h",
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdnoreturn.h",
)

# #include_next is how these headers defer to a hosted libc, which freestanding mode never does,
# so only plain includes are followed.
INCLUDE = re.compile(r"^\s*#\s*include\s*<([^>]+)>", re.MULTILINE)


def make_shim(cc: list[str], output: Path) -> None:
    resource = subprocess.run(
        [*cc, "-print-resource-dir"], capture_output=True, text=True, check=True
    ).stdout.strip()
    source = Path(resource) / "include"

    wanted = list(FREESTANDING)
    for name in wanted:
        header = source / name
        if not header.is_file():
            raise SystemExit(f"{header} doesn't exist, so {cc[0]} has no freestanding {name}")
        for included in INCLUDE.findall(header.read_text()):
            if included not in wanted and (source / included).is_file():
                wanted.append(included)

    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    for name in wanted:
        shutil.copy(source / name, output / name)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    make_shim(args.cc.split(), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
