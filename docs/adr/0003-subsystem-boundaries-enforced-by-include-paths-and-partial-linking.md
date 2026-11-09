# Subsystem boundaries are enforced by include paths and partial linking

Every subsystem's allowed dependencies are declared in one central file, and the build enforces them in three layers, so a broken boundary fails the ordinary build on macOS and in CI alike:

1. **Include paths.** A subsystem compiles with its own directory, the `include/` directories of its declared dependencies and the compiler's freestanding headers, and nothing else. Dependencies aren't transitive.
2. **Private symbols are hidden.** Sources compile with `-fvisibility=hidden`, and exports are marked with a macro on their public declarations. Each subsystem is partially linked into one relocatable object (`ld.lld -r`), then `llvm-objcopy --localize-hidden` makes every symbol it doesn't export local. Assembly declares symbols through macros that emit `.hidden` unless the symbol is exported, and raw `.globl` is rejected.
3. **Outside references are checked.** Each subsystem object's undefined symbols must be exported by a declared dependency. The only exceptions are the compiler-emitted `memcpy`, `memset`, `memmove` and `memcmp`, plus, for the port, the port entry points listed in the central declaration. Exported symbols must carry their subsystem's prefix (`mm_alloc`). The port entry points are the exception: they carry the port interface's neutral `k` prefix (`kmain`, `kpanic`, `kprint`), so a port never names the subsystem that implements them ([ADR 0002](0002-acyclic-subsystem-graph-and-port-interface.md)).

Include paths alone stop accidents but not a hand-written `extern` or assembly, which never touches include paths. The link layers close that gap and keep the declared graph the real one. Must-fail fixtures, one per rule, keep the checks from going quietly dead.

## Considered Options

- **Convention and code review only.** Rejected: the modular monolith promises boundaries enforced at build time, and a convention isn't enforced.
- **Include paths only.** Rejected: an `extern` declaration or a `call` from assembly crosses any boundary unnoticed.
- **CMake-style interface dependencies, whose include paths propagate to dependents.** Rejected: a subsystem could then use a dependency of a dependency without declaring it.
- **An export list file per subsystem (`--keep-global-symbols`).** Rejected in favour of the macro: every export would be named twice, and the public header is already the interface.

## Consequences

- Private names can't collide between subsystems, so only exports need a prefix.
- Link-time optimisation can't cross a subsystem boundary, because each subsystem is linked on its own first.
- A subsystem is already a relocatable object with a defined set of exports, which is the shape a loadable module would take later.
