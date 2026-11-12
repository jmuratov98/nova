#!/usr/bin/env python3
"""Checks that the machine can build Nova, before anything is built.

Nova builds with clang and LLVM's ld.lld, llvm-objcopy and llvm-nm (ADR 0005). This checks that
each is installed and is the real thing, and then that together they can do what the build asks
of them: compile with the kernel's flags, partially link, hide symbols and read them back. If
anything is wrong it prints one line that says everything that is, and exits 1. Otherwise it
prints nothing.

    check_env.py --cc CC --ld LD --objcopy OBJCOPY --nm NM -- KERNEL_CFLAGS...

The Python version and GNU Make's are checked by the Makefile, before this runs.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROBE = "int nova_probe(void);\nint nova_probe(void) { return 0; }\n"
INSTALL = "See docs/building.md for what to install on macOS and on Linux"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def first_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else "it printed nothing"


def identify(command: list[str], flag: list[str], marker: str) -> bool:
    """Whether the tool's output for a flag mentions marker. A GCC and GNU binutils tool exist
    under the same names, and mustn't pass for LLVM's."""
    done = run([*command, *flag])
    return marker in done.stdout + done.stderr


def check(cc: str, ld: str, objcopy: str, nm: str, cflags: list[str]) -> list[str]:
    tools = {"CC": cc, "LD": ld, "OBJCOPY": objcopy, "NM": nm}
    problems = []
    found = {}
    for variable, value in tools.items():
        if shutil.which(shlex.split(value)[0]) is None:
            problems.append(f"{variable} '{value}' was not found")
        else:
            found[variable] = shlex.split(value)

    if "CC" in found and not identify(
        found["CC"], ["-dM", "-E", "-x", "c", "/dev/null"], "__clang__"
    ):
        problems.append(f"CC '{cc}' isn't clang, and GCC isn't supported")
        del found["CC"]
    if "LD" in found and not identify(found["LD"], ["--version"], "LLD"):
        problems.append(f"LD '{ld}' isn't LLVM's ld.lld")
        del found["LD"]
    for variable, marker in (("OBJCOPY", "LLVM"), ("NM", "LLVM")):
        if variable in found and not identify(found[variable], ["--version"], marker):
            problems.append(f"{variable} '{tools[variable]}' isn't LLVM's")
            del found[variable]

    if len(found) == len(tools):
        problem = probe(found, cflags)
        if problem:
            problems.append(problem)

    return problems


def probe(found: dict[str, list[str]], cflags: list[str]) -> str | None:
    """Builds a one-function subsystem the way the build does. Returns what went wrong."""
    with tempfile.TemporaryDirectory(prefix="nova-probe-") as scratch:
        source = Path(scratch, "probe.c")
        source.write_text(PROBE)
        obj, linked, hidden = (str(Path(scratch, name)) for name in ("a.o", "b.o", "c.o"))
        steps = [
            (
                "compile with Nova's kernel flags",
                [*found["CC"], *cflags, "-c", "-o", obj, str(source)],
            ),
            ("partially link with -r", [*found["LD"], "-r", "-o", linked, obj]),
            ("localize hidden symbols", [*found["OBJCOPY"], "--localize-hidden", linked, hidden]),
            ("list symbols", [*found["NM"], hidden]),
        ]
        for what, command in steps:
            done = run(command)
            if done.returncode != 0:
                return f"{command[0]} can't {what}: {first_line(done.stderr + done.stdout)}"
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cc", required=True)
    parser.add_argument("--ld", required=True)
    parser.add_argument("--objcopy", required=True)
    parser.add_argument("--nm", required=True)
    parser.add_argument("cflags", nargs="*")
    args = parser.parse_args(argv)

    problems = check(args.cc, args.ld, args.objcopy, args.nm, args.cflags)
    if problems:
        print(f"Cannot build Nova: {'; '.join(problems)}. {INSTALL}")  # make adds the final period
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
