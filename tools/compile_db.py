#!/usr/bin/env python3
"""Writes the compile database that clang-tidy and editors read, from the commands the build uses.

The build hands over what it compiles with, as groups of sources that share one command, and this
writes each source's entry. Asking the compiler to record its own commands (clang's -MJ) isn't an
option, because Apple clang adds `-Xclang -clang-vendor-feature=...` there, which clang-tidy 23
rejects as a compiler error.

    compile_db.py --directory DIR --output FILE [--group COMMAND SOURCES]...

COMMAND is the compiler and its flags as one shell-quoted string, and SOURCES the files that it
compiles, separated by spaces and relative to DIR. FILE is only written when its contents change,
so that whatever depends on it is only redone when they do.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path


def entries(directory: str, groups: list[list[str]]) -> list[dict[str, object]]:
    """One entry for each source, sorted by file so that the output doesn't depend on make's
    order."""
    found = []
    for command, sources in groups:
        arguments = shlex.split(command)
        for source in sources.split():
            found.append(
                {"directory": directory, "file": source, "arguments": [*arguments, "-c", source]}
            )
    return sorted(found, key=lambda entry: str(entry["file"]))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--directory", required=True, help="what the commands run in")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--group",
        nargs=2,
        action="append",
        default=[],
        metavar=("COMMAND", "SOURCES"),
        help="a compile command and the sources that it compiles",
    )
    args = parser.parse_args(argv)

    text = json.dumps(entries(args.directory, args.group), indent=2) + "\n"
    if not args.output.is_file() or args.output.read_text() != text:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
