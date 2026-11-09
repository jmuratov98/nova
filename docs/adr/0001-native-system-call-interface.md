# Nova has its own system-call interface, not Linux's

Nova defines its own system-call numbering and conventions instead of copying Linux's, so the interface is designed for Nova and not inherited from Linux. glibc was the libc we first had in mind, but it supports only Linux and GNU Hurd and is very hard to port to a new kernel. Nova will therefore port mlibc, which is built to be ported to new kernels, and may later have one of its own. The system-call interface is shaped to fit mlibc's port interface.

The data a libc decodes still follows Linux's: errno values, signal numbers, the wait-status encoding, auxiliary-vector keys and the sizes of types such as `pid_t`. Nearly every mlibc port uses Linux's definitions for these, including the ports to kernels that aren't Linux, and designing new tables would teach nothing.

## Considered Options

- **Linux system-call compatibility**: unmodified glibc and static Linux binaries would run immediately. We rejected it because Nova would then have to match Linux's behaviour well beyond POSIX (`clone`, `futex`, `/proc` expectations), and designing the interface ourselves is part of the point.
- **Porting glibc to Nova's own interface**: rejected as the hardest route for the least gain.
- **Porting musl**: rejected because musl is written for Linux. It calls Linux system calls by number throughout, so it would need a layer that translates them into Nova's.
