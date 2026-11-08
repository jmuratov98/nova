# Nova has its own system-call interface, not Linux's

Nova defines its own system-call numbering and conventions instead of copying Linux's, so the interface is designed for Nova and not inherited from Linux. glibc was the libc we first had in mind, but it supports only Linux and GNU Hurd and is very hard to port to a new kernel. Nova will therefore port a libc built for new kernels (such as mlibc or musl) and may later have one of its own.

## Considered Options

- **Linux system-call compatibility**: unmodified glibc and static Linux binaries would run immediately. We rejected it because Nova would then have to match Linux's behaviour well beyond POSIX (`clone`, `futex`, `/proc` expectations), and designing the interface ourselves is part of the point.
- **Porting glibc to Nova's own interface**: rejected as the hardest route for the least gain.
