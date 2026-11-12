#!/usr/bin/env python3
"""Checks the tools that `make lint` and `make format` run, against the versions that CI pins.

A tool that isn't installed is an error, since there is nothing to run, and this prints one line
that says which and exits 1. A tool whose version isn't the pin is only a warning, because CI is
the reference and what is installed locally is whatever it is. LLVM's tools are compared by major
version and ruff's exactly.

    check_lint_tools.py --llvm-version VERSION --ruff-version VERSION
                        [--clang-format COMMAND] [--clang-tidy COMMAND] [--ruff COMMAND]

Only the tools that are named are checked, so that `make format` doesn't need clang-tidy.
"""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass

INSTALL = "See docs/building.md for what to install on macOS and on Linux"


@dataclass(frozen=True)
class Kind:
    """How a tool says which version it is, and what its pin means."""

    pattern: re.Pattern[str]  # --version's output has the version in its first group
    pin: str  # what the pin is, for the warning: "major version" or "release"


# For LLVM's tools, whatever a distribution puts in front, it is "version 23.1.2": "clang-format
# version 23.1.2", "Homebrew LLVM version 23.1.4". Ruff's is "ruff 0.17.5".
LLVM = Kind(re.compile(r"\bversion (\d+)\.\d+\.\d+"), "major version")
RUFF = Kind(re.compile(r"\bruff (\S+)"), "release")
KINDS = {"clang-format": LLVM, "clang-tidy": LLVM, "ruff": RUFF}


def version_of(command: list[str], kind: Kind) -> str | None:
    done = subprocess.run([*command, "--version"], capture_output=True, text=True, check=False)
    found = kind.pattern.search(done.stdout + done.stderr)
    return found.group(1) if found else None


def check(tools: dict[str, str], pins: dict[str, str]) -> tuple[list[str], list[str]]:
    """Returns the problems, which stop the lint, and the warnings, which don't. Both dicts are
    keyed by tool name: tools has the command for each, and pins the version that CI pins."""
    problems = []
    warnings = []
    for name, value in tools.items():
        command = shlex.split(value)
        if shutil.which(command[0]) is None:
            problems.append(f"{name} '{value}' was not found")
            continue
        kind = KINDS[name]
        found = version_of(command, kind)
        if found is None:
            warnings.append(f"can't tell which version of {name} '{value}' this is")
        elif found != pins[name]:
            warnings.append(f"{name} is {found}, but CI pins {kind.pin} {pins[name]}")
    return problems, warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--llvm-version", required=True, help="the LLVM major version CI pins")
    parser.add_argument("--ruff-version", required=True, help="the ruff release that CI pins")
    parser.add_argument("--clang-format")
    parser.add_argument("--clang-tidy")
    parser.add_argument("--ruff")
    args = parser.parse_args(argv)

    commands = {"clang-format": args.clang_format, "clang-tidy": args.clang_tidy, "ruff": args.ruff}
    tools = {name: command for name, command in commands.items() if command is not None}
    pins = {
        "clang-format": args.llvm_version,
        "clang-tidy": args.llvm_version,
        "ruff": args.ruff_version,
    }

    problems, warnings = check(tools, pins)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if problems:
        print(f"Cannot lint or format Nova: {'; '.join(problems)}. {INSTALL}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
