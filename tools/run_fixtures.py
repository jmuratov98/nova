#!/usr/bin/env python3
"""Runs the fixtures: a must-fail one for each rule that the build enforces, and must-pass ones
for what the rules permit, so that they aren't too strict either.

A fixture is a directory under tests/fixtures/ with a fixture.toml and a files/ tree. The runner
copies the build's sources to a scratch directory, lays the fixture's files over the copy, and
runs make there, so that the fixture goes through the same rules as the real build. A must-fail
fixture passes if the build fails and prints the fixture's stable message. A build that
succeeds, one that fails with some other message, and a tool that crashes all fail it.

fixture.toml:
    description  what the fixture does, and why it is or isn't a violation
    expect       the stable message, which must appear in the build's output. A fixture without
                 one must pass: the build has to succeed
    goal         the make goal, kernel by default
    make_args    more make arguments, empty by default
    remove       files to delete from the copy, empty by default
    append       a table of file to text, which is added to the end of that file in the copy, so
                 that a fixture can extend kernel/subsystems.toml without copying all of it

    run_fixtures.py [--only NAME] --make MAKE [-- VARIABLE=VALUE...]

The variables after -- are passed on to every make, so that the fixtures use the same toolchain as
the build that runs them.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

FIXTURES = Path("tests/fixtures")
# What a build needs from the repository. Output, git and the fixtures themselves stay behind.
COPIED = ("Makefile", "config.mk", "mk", "tools", "kernel", "third_party")
TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class Fixture:
    name: str
    description: str
    expect: str  # empty for a fixture that must pass
    goal: str
    make_args: tuple[str, ...]
    remove: tuple[str, ...]
    append: dict[str, str]
    files: Path


def load(directory: Path) -> Fixture:
    spec = tomllib.loads((directory / "fixture.toml").read_text())
    return Fixture(
        name=directory.name,
        description=spec["description"],
        expect=spec.get("expect", ""),
        goal=spec.get("goal", "kernel"),
        make_args=tuple(spec.get("make_args", ())),
        remove=tuple(spec.get("remove", ())),
        append=dict(spec.get("append", {})),
        files=directory / "files",
    )


def run(fixture: Fixture, root: Path, make: list[str], forwarded: list[str]) -> str | None:
    """Returns why the fixture failed, or None if it passed."""
    with tempfile.TemporaryDirectory(prefix=f"nova-fixture-{fixture.name}-") as scratch_name:
        scratch = Path(scratch_name)
        for name in COPIED:
            source = root / name
            if source.is_dir():
                shutil.copytree(
                    source, scratch / name, ignore=shutil.ignore_patterns("__pycache__")
                )
            elif source.is_file():
                shutil.copy2(source, scratch / name)
        if fixture.files.is_dir():
            shutil.copytree(fixture.files, scratch, dirs_exist_ok=True)
        for name in fixture.remove:
            (scratch / name).unlink()
        for name, text in fixture.append.items():
            with (scratch / name).open("a") as file:
                file.write(text)

        # A make that this one started would otherwise inherit its jobserver and its variables.
        env = {k: v for k, v in os.environ.items() if k not in ("MAKEFLAGS", "MAKELEVEL", "MFLAGS")}
        command = [
            *make,
            fixture.goal,
            *forwarded,
            f"BUILD_DIR={scratch / 'build'}",
            *fixture.make_args,
        ]
        try:
            done = subprocess.run(
                command,
                cwd=scratch,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return f"make didn't finish in {TIMEOUT_SECONDS} seconds"

    output = done.stdout + done.stderr
    if not fixture.expect:
        return None if done.returncode == 0 else f"the build failed:\n{output}"
    if done.returncode == 0:
        return "the build succeeded"
    if "Traceback (most recent call last)" in output:
        return f"a tool crashed:\n{output}"
    if fixture.expect not in output:
        return f"the build failed without the message {fixture.expect!r}:\n{output}"
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--make", default="make", help="the make to run, as a command")
    parser.add_argument("--only", help="run just this fixture")
    parser.add_argument("forwarded", nargs="*", help="VARIABLE=VALUE for every make")
    args = parser.parse_args(argv)

    root = Path.cwd()
    fixtures = [
        load(d) for d in sorted((root / FIXTURES).iterdir()) if (d / "fixture.toml").is_file()
    ]
    if args.only:
        fixtures = [f for f in fixtures if f.name == args.only]
        if not fixtures:
            print(f"there is no fixture named {args.only}", file=sys.stderr)
            return 1

    make = shlex.split(args.make)
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        results = list(pool.map(lambda f: run(f, root, make, args.forwarded), fixtures))

    failed = 0
    for fixture, why in zip(fixtures, results, strict=True):
        if why is None:
            print(f"  PASS  {fixture.name}")
        else:
            failed += 1
            print(f"  FAIL  {fixture.name}: {fixture.description}\n        {why}")
    print(f"{len(fixtures)} fixtures, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
