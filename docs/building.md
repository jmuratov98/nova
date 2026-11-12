# Building Nova

```
gmake kernel    # on macOS
make kernel     # on Linux
```

builds a linked x86-64 kernel at `build/x86_64/kernel.elf`. `make check` then runs the fixtures that
keep the build's rules from going quietly dead. Neither needs QEMU, a boot image or the network.

## Prerequisites

The build checks all of these before it starts, and stops with one message that says what is missing.

| Need | Why |
|---|---|
| GNU Make 4.3 or newer | drives the build |
| Python 3.11 or newer, standard library only | the boundary checks and the declaration tool |
| clang, any version, Apple clang included | compiles. GCC isn't supported ([ADR 0005](adr/0005-clang-and-llvm-binary-tools-not-gcc.md)) |
| `ld.lld`, `llvm-objcopy`, `llvm-nm` | link the subsystems and enforce their boundaries |
| `clang-format`, `clang-tidy`, `ruff` | only for `make lint` and `make format` |

### macOS

```
brew bundle
```

installs everything in the `Brewfile`. macOS's own `make` is 3.81, which is too old, so run Homebrew's
as `gmake`. Homebrew's `llvm` is keg-only, and the build looks in its directory without it being on
`PATH`. Homebrew's `python3` has to come before `/usr/bin/python3` on `PATH`, which is what a
Homebrew install normally does.

### Linux

CI builds with LLVM 23 from [apt.llvm.org](https://apt.llvm.org), on Ubuntu:

```
sudo apt install make python3 clang-23 lld-23 llvm-23
```

That installs the tools with versioned names (`clang-23`, `ld.lld-23`). Either put
`/usr/lib/llvm-23/bin` on `PATH`, where they have their plain names, or name them in `config.mk`.

`make lint` also needs `clang-format-23` and `clang-tidy-23` from the same repository, and ruff at
the release that [`mk/versions.env`](../mk/versions.env) pins, which `pip install ruff==<release>`
installs.

### Per-machine settings

Copy `config.mk.example` to `config.mk`. Git ignores it. It sets `CC`, `LD`, `OBJCOPY`, `NM`,
`PYTHON`, `CLANG_FORMAT`, `CLANG_TIDY` and `RUFF`, and anything on the command line wins over it.

## Targets and variables

| | |
|---|---|
| `make kernel` | build the kernel. It is the default target until the boot image exists |
| `make check` | build the kernel, then run the fixtures |
| `make lint` | check formatting, run clang-tidy and ruff |
| `make format` | rewrite C and Python in place to the style that `make lint` checks |
| `make clean` | remove the build output for `ARCH` |
| `make distclean` | remove the whole build directory, if Nova made it |
| `ARCH=` | the port. `x86_64` is the default, and the only one |
| `OPT=` | replaces `-O2 -g` |
| `WERROR=` | empty turns off `-Werror`, for a local clang that is newer than CI's |
| `V=1` | print each command in full |
| `BUILD_DIR=` | where output goes, `build` by default |

Output goes out of tree, to `$(BUILD_DIR)/$(ARCH)/`. The kernel is compiled as freestanding C17 with
`-nostdinc`, and a header shim, `build/x86_64/shim/`, holds only the compiler's copies of C17's nine
freestanding headers. UBSan traps and needs no runtime. Link-time optimisation is off.

## Lint and format

`make lint` runs, on every file of Nova's own code (`kernel/`, `user/`, `tests/`, `tools/` and
`mk/`, and never `third_party/`):

- `clang-format --dry-run` on each `.c` and `.h`, against the root `.clang-format`: LLVM style,
  4-space indents, 100 columns, braces inserted, and C17's freestanding headers in an include
  block of their own. Assembly and `third_party/` aren't formatted, and `.clang-format-ignore`
  keeps an editor from doing it;
- `clang-tidy` on each C source that the build compiles, against the root `.clang-tidy`;
- `ruff check` and `ruff format --check` on each `.py`, against `ruff.toml`, which sets only
  `line-length = 100`.

`make format` rewrites the same C and Python files in place. It needs neither a toolchain nor
clang-tidy.

Each file is checked on its own, so a second run does only what changed. Editing a header, the
prelude or a configuration file redoes every clang-tidy check, since any source may read it.
`make lint` goes on after a failure, so one run reports every file that fails.

CI runs `make lint` as a job of its own, so that a style issue never stops the tests from
running. It installs only LLVM 23 and ruff, at the versions in
[`mk/versions.env`](../mk/versions.env), which the Makefile and the workflow both read. Locally `make lint` runs whatever is installed
and prints a warning, not an error, when a tool isn't the pinned version. CI is the reference.
Only a missing tool stops it. On macOS, `llvm` provides clang-format and clang-tidy and `ruff` is
in the `Brewfile`.

### clang-tidy

It enables `clang-analyzer-*`, `bugprone-*`, `misc-*` and `portability-*`, and five readability
checks, and every finding is an error. `.clang-tidy` says why each of the three checks it
disables is off. A finding that is a false alarm gets a `NOLINT` on its line that names the check
and says why, as in `// NOLINT(bugprone-foo): the reason`. A bare `NOLINT` isn't accepted.

The port has a `.clang-tidy` of its own that turns off `portability-no-assembler` and nothing
else. A port is made of inline assembly, which only the port may contain, so the check has nothing
to say there, and it is still on everywhere else.

Recursion is one of what it catches (`misc-no-recursion`, because kernel stacks are 16 KiB). Statement
expressions, `##__VA_ARGS__` and `{}` initialisers are the compiler's job, through `-Wpedantic`.

### The compile database

clang-tidy reads `build/<arch>/compile_commands.json`, which every build writes itself, from the
variables it compiles with and not from clang's `-MJ`. That option is no use here, because Apple
clang adds `-Xclang -clang-vendor-feature=...` to what it records, and clang-tidy 23 rejects that as
an error. The committed `.clangd` points editors at the same file, so build once and they have it.

Something that compiles C registers it in `NOVA_COMPDB`. Each subsystem does in `mk/kernel.mk`,
with the command in `<name>.compdb` and its sources in `<name>.srcs`, and compiles with that
command. Userland and the host tests will do the same when they exist, and clang-tidy then covers
them too.

## Subsystems and their boundaries

The kernel is a modular monolith: subsystems that may reach only the subsystems they declare
([ADR 0002](adr/0002-acyclic-subsystem-graph-and-port-interface.md),
[ADR 0003](adr/0003-subsystem-boundaries-enforced-by-include-paths-and-partial-linking.md)).
`kernel/subsystems.toml` is the one place that declares them. The build checks that it is acyclic
and matches the directories under `kernel/`, and generates every subsystem's include paths from it.

```
kernel/
  subsystems.toml        the declaration
  lib/
    include/lib/*.h      public headers, which subsystems that depend on lib can include
    *.c *.S *.h          everything else is private to lib
  port/
    include/port/*.h     the port interface, which every port implements
    x86_64/              the one port, with port.mk, its linker script and its own headers
```

### How a boundary is enforced

1. **Include paths.** A subsystem compiles with its own directory, the `include/` directories of
   its declared dependencies and the nine freestanding headers, and nothing else. An include by a
   relative path, or one that a macro spells, doesn't use the include paths, so after compiling the
   build also checks every file that the compiler says it opened, however the include was spelled.
   A vendored header is allowed one file at a time, though the compiler searches its directory.
2. **Private symbols are hidden.** Sources compile with `-fvisibility=hidden`. A public header
   marks what the subsystem exports with `NOVA_EXPORT`. Each subsystem is partially linked into one
   relocatable object (`ld.lld -r`), and `llvm-objcopy --localize-hidden` makes everything it
   doesn't export local. Assembly declares symbols with `NOVA_FUNC` (private) and
   `NOVA_EXPORT_FUNC` (exported), and never with `.globl`. Both macros and `NOVA_EXPORT` are in
   `mk/prelude.h`, which the build includes into every source.
3. **Outside references are checked.** Every undefined symbol in a subsystem's object must be
   exported by a subsystem that it declares, and every export must start with its subsystem's
   name and an underscore, as `lib_` does. The exceptions are `lib`'s `memcpy`, `memset`,
   `memmove` and `memcmp`, and the port's entry points, which start with `k`.

Source checks cover what these can't: portable code, which is everything outside
`kernel/port/<ARCH>/`, never tests an architecture macro, contains no inline `asm` and includes
only the port interface's headers. The port interface's own headers may include the port's
supplements, which hold types and constants, so portable code can get them that way. Every file
under `kernel/` is checked, whatever its extension, except the declaration, `.mk` files and linker
scripts.

The source checks read the text, so they catch mistakes and not someone set on evading them, for
instance with a macro that builds a directive's name. The checks on the opened headers and on the
symbols don't read text, and they are what holds when the source checks miss.

### Reading an error

Every error names its rule, and the fixtures assert these names.

| Rule | Reported by | What broke |
|---|---|---|
| `file not found` for a header | the compiler | included a header of a subsystem that isn't a dependency |
| `forbidden-include` | header check | the compiler opened a header outside what the subsystem may include, such as by a relative path or through a macro, or a vendored header that isn't permitted |
| `port-private-include` | source check | portable code included a header that belongs to the port |
| `arch-macro`, `inline-asm` | source check | portable code depends on the architecture |
| `raw-globl` | source check | declared a symbol with `.globl`, `.global`, `.weak` or `.comm`, in any case |
| `private-symbol` | symbol check | referenced a symbol that a dependency doesn't export |
| `undeclared-dependency` | symbol check | referenced an export of a subsystem that isn't a dependency |
| `unresolved-symbol` | symbol check | referenced a symbol that no subsystem defines |
| `export-prefix` | symbol check | exported a symbol without its subsystem's prefix |
| `missing-declaration`, `malformed-declaration`, `cyclic-dependency`, `unknown-dependency`, `missing-directory`, `undeclared-directory`, `missing-port`, `unknown-third-party-header` | declaration | `subsystems.toml` is wrong or disagrees with the disk |
| `kernel-image` | kernel check | the linked kernel has no entry point, or isn't an x86-64 executable |

### Adding a subsystem

Add its directory and its table in `kernel/subsystems.toml` in the same change. Name what it
depends on, since dependencies aren't transitive. Put the public headers under
`include/<name>/`, and start every export's name with `<name>_`.

A port is a directory `kernel/port/<arch>/` with a `port.mk`, which sets the target triple, the
codegen flags, the linker script and the entry point.

## Fixtures

`tests/fixtures/<name>/` holds one fixture. `fixture.toml` says what it breaks and the stable
message that the build must print, and `files/` is laid over a copy of the build's sources. `make
check` runs each one through the real build rules in a scratch directory and fails if a fixture
that should fail builds, or fails with another message. A fixture with no `expect` must build.
`tools/run_fixtures.py --only <name>` runs one.
