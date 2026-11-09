# System calls return a value and an error in two registers

Every Nova system call returns a pair: a value, and an error that is 0 on success or a positive errno. The pair comes back in the two registers each architecture's C ABI uses to return a struct of two 64-bit integers (`rax`:`rdx` on x86-64, `x0`:`x1` on AArch64, `a0`:`a1` on RISC-V). Kernel handlers and userland stubs therefore share one struct with no conversion, and a value can never be mistaken for an error.

## Considered Options

- **Linux's negative errno in one register**: rejected because every call that returns a value gives up the top 4095 values of its range, and Nova's interface isn't Linux's anyway ([ADR 0001](0001-native-system-call-interface.md)).
- **Error only, with results through out-pointers**: this matches mlibc's port interface exactly, but every result costs a write to user memory, even for `getpid`.
