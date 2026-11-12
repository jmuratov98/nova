#!/usr/bin/env python3
"""Checks which headers the compiler opened (ADR 0003, layer 1).

The include paths keep a subsystem to its own directory and its dependencies' public ones, but an
include by a relative path doesn't use them, and neither does one that a macro spells. The
compiler writes every file it opened to a dependency file, however the include was spelled, so
this reads those instead of the text.

Run after every subsystem has been compiled.

    check_headers.py [--arch ARCH] --build-dir DIR [--allow FILE]...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import subsystems
from subsystems import Declaration


def read_dependencies(depfile: Path) -> list[str]:
    """The files that the compiler opened, from a make-style dependency file."""
    # The first rule names every file. -MP adds an empty rule for each header after it.
    rule = depfile.read_text().replace("\\\n", " ").split("\n", 1)[0]
    files = rule.partition(": ")[2].strip()
    return [name.replace("\\ ", " ") for name in re.split(r"(?<!\\)\s+", files) if name]


def check(declaration: Declaration, build_dir: Path, allowed: list[str]) -> list[str]:
    root = declaration.root.resolve()
    errors = []
    for name in declaration.subsystems:
        directories, vendored = declaration.may_include(name)
        # The freestanding headers are in the shim, which the compiler doesn't list.
        may_be_in = [(root / d).resolve() for d in directories] + [(build_dir / "shim").resolve()]
        may_be = {(root / f).resolve() for f in [*vendored, *allowed]}

        for source in declaration.sources(name):
            depfile = build_dir / "obj" / name / f"{Path(source).name}.d"
            for header in dict.fromkeys(read_dependencies(depfile)):
                path = (root / header).resolve()
                if path in may_be or any(path.is_relative_to(d) for d in may_be_in):
                    continue
                shown = path.relative_to(root) if path.is_relative_to(root) else path
                errors.append(
                    f"{source}: error: forbidden-include: {name} includes {shown.as_posix()}, "
                    f"which is outside what {name} may include: its own directory, its "
                    f"dependencies' public headers and the vendored headers it is permitted"
                )
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--arch", default="x86_64")
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--allow", action="append", default=[], help="a header for every source")
    args = parser.parse_args(argv)

    try:
        declaration = subsystems.load(args.root, args.arch)
    except subsystems.DeclarationError as error:
        print(error, file=sys.stderr)
        return 1

    errors = check(declaration, args.build_dir, args.allow)
    for message in errors:
        print(message, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
