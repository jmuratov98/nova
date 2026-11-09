# Nova builds with clang and LLVM's binary tools, not GCC

Any clang compiles Nova, Apple clang included, and LLVM's `ld.lld`, `llvm-objcopy` and `llvm-nm` always link it and run the boundary checks. GCC and GNU binutils aren't supported. One clang binary targets all three planned ports through `--target`, where GCC needs a separate cross-compiler for each. The boundary enforcement in [ADR 0003](0003-subsystem-boundaries-enforced-by-include-paths-and-partial-linking.md) was also built and verified on lld's partial linking, `llvm-objcopy --localize-hidden` and `llvm-nm`'s output. CI builds with one pinned clang, LLVM 23 from apt.llvm.org, and is the reference. A local build accepts whichever clang is installed.

## Considered Options

- **A cross-GCC with GNU binutils**, the usual advice for hobby kernels: rejected because each port needs its own toolchain (`x86_64-elf-gcc`, `aarch64-elf-gcc`, `riscv64-elf-gcc`). Homebrew's plain `gcc` is a native Darwin compiler and can't build an x86-64 kernel.
- **Both clang and GCC, each with a CI job**: a second compiler catches non-portable C. Rejected because every flag needs two spellings, CI time doubles, and Ubuntu has no `x86_64-elf-gcc`, so CI would have to use a native GCC with its distro defaults (PIE, stack protector, CET) switched off.
- **Exactly LLVM 23 everywhere**: rejected because Homebrew moves `llvm` to a new major on its own, and Apple clang already builds x86-64 ELF objects.

## Consequences

- Apple clang has no RISC-V backend, so the RISC-V port will need Homebrew clang on macOS.
- With one compiler family, nothing catches code that only clang accepts. Warnings and static analysis have to.
