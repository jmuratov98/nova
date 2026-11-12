#!/usr/bin/env python3
"""Checks the tools that `make lint` and `make format` run, against the versions that CI pins.

A tool that isn't installed is an error, since there is nothing to run, and this prints one line
that says which and exits 1. A tool whose version isn't the pin is only a warning, because CI is
the reference and what is installed locally is whatever it is. LLVM's tools are compared by major
version and ruff's exactly.

    check_lint_tools.py --llvm VERSION --ruff-version VERSION
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

INSTALL = "See docs/building.md for what to install on macOS and on Linux"

# How --version gives the version. For LLVM's tools, whatever a distribution puts in front, it
# is "version 23.1.2": "clang-format version 23.1.2", "Homebrew LLVM version 23.1.4". Ruff's is
# "ruff 0.17.5".
LLVM_VERSION = re.compile(r"\bversion (\d+)\.\d+\.\d+")
RUFF_VERSION = re.compile(r"\bruff (\S+)")


def version_of(command: list[str], pattern: re.Pattern[str]) -> str | None:
    done = subprocess.run([*command, "--version"], capture_output=True, text=True, check=False)
    found = pattern.search(done.stdout + done.stderr)
    return found.group(1) if found else None


def check(tools: dict[str, str], llvm: str, ruff: str) -> tuple[list[str], list[str]]:
    """Returns the problems, which stop the lint, and the warnings, which don't."""
    problems = []
    warnings = []
    for name, value in tools.items():
        command = shlex.split(value)
        if shutil.which(command[0]) is None:
            problems.append(f"{name} '{value}' was not found")
            continue
        is_ruff = name == "ruff"
        pin = ruff if is_ruff else llvm
        found = version_of(command, RUFF_VERSION if is_ruff else LLVM_VERSION)
        if found is None:
            warnings.append(f"can't tell which version of {name} '{value}' this is")
        elif found != pin:
            what = "release" if is_ruff else "major version"
            warnings.append(f"{name} is {found}, but CI pins {what} {pin}")
    return problems, warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--llvm", required=True, help="the LLVM major version that CI pins")
    parser.add_argument("--ruff-version", required=True, help="the ruff release that CI pins")
    parser.add_argument("--clang-format")
    parser.add_argument("--clang-tidy")
    parser.add_argument("--ruff")
    args = parser.parse_args(argv)

    tools = {
        name: value
        for name, value in (
            ("clang-format", args.clang_format),
            ("clang-tidy", args.clang_tidy),
            ("ruff", args.ruff),
        )
        if value is not None
    }
    problems, warnings = check(tools, args.llvm, args.ruff_version)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if problems:
        print(f"Cannot lint or format Nova: {'; '.join(problems)}. {INSTALL}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
