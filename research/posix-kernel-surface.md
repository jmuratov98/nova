# Kernel-facing surface POSIX.1-2024 requires

Research for [#2](https://github.com/jmuratov98/nova/issues/2) (child of map [#1](https://github.com/jmuratov98/nova/issues/1)).
Question: which POSIX.1-2024 interfaces need kernel support rather than being implementable purely in a libc, grouped by area, with each area's POSIX option and whether it is mandatory for a base-conforming system; and does base conformance require working `AF_INET` sockets?

Facts only: this file records what the standard says. It makes no recommendation about Nova's Milestones.

## Sources

All normative citations are to **IEEE Std 1003.1-2024 / The Open Group Base Specifications Issue 8** (SUSv5), online edition, base URL `https://pubs.opengroup.org/onlinepubs/9799919799/` (read 2026-11-20). Short names used below:

| Name | Page |
| --- | --- |
| XBD 2 (Conformance) | <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html> |
| XBD 1.8.1 (Margin codes) | <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_08_01> |
| XBD 10 (Directory Structure and Devices) | <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap10.html> |
| XBD 11 (General Terminal Interface) | <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap11.html> |
| `<unistd.h>` (option constants) | <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html> |
| XSH 2 (General Information, incl. 2.10 Sockets) | <https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html> |
| XRAT A (definitions rationale) | <https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xbd_chap01.html> |
| XRAT B (system interfaces rationale) | <https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html> |
| Per-header pages | `https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/<header>.html`, e.g. [`sys_socket.h.html`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_socket.h.html) |

**Method.** The option marking of every interface in the inventory was read off the per-header pages: the margin code in front of each prototype, plus the page-level code in the SYNOPSIS for headers that are optional as a whole (`<mqueue.h>` MSG, `<spawn.h>` SPN, `<devctl.h>` DC; `<sys/ipc.h>`, `<sys/msg.h>`, `<sys/sem.h>`, `<sys/shm.h>`, `<sys/uio.h>`, `<sys/time.h>`, `<utmpx.h>` XSI). An interface with no margin code, or only `[CX]`, is mandatory: CX marks "an extension to the ISO C standard… supported on all POSIX.1-2024-conforming systems" ([XBD 1.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_08_01)). An interface counted as "removed" returns HTTP 404 from the Issue 8 online edition and is absent from the header page.

One non-POSIX source is cited once, for an implementation precedent: the Linux man-pages project's [aio(7)](https://man7.org/linux/man-pages/man7/aio.7.html).

## Headline answers

1. **POSIX does not define "kernel" versus "libc".** XRAT A: "The distinction between a 'system call' and a 'library routine' is an implementation detail that may differ between implementations and has thus been excluded from POSIX.1" ([XRAT A, System Call](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xbd_chap01.html#tag_21_03_00_125)). The kernel-facing classification below is therefore an analysis, not a statement the standard makes (see "Classification basis").
2. **Base conformance is large.** A conforming system "shall support all the mandatory functions and headers" and must set 15 former options to `202405L`: asynchronous I/O, barriers, clock selection, mapped files, memory protection, monotonic clock, reader-writer locks, realtime signals, semaphores, spin locks, thread-safe functions, threads, timeouts, timers, C binding. Job control, regexp, saved IDs and shell must be greater than zero ([XBD 2.1.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_03)). The standard notes: "The symbols above represent historical options that are no longer allowed as options."
3. **Threads and realtime signals are not options.** The ticket names THR and RTS as example options. POSIX.1-2024 has no THR or RTS margin code; the full list of codes is ADV CD CPT CX DC FR FSC IP6 MC1 ML MLR MSG MX MXC MXX OB OF OH PIO PS RPI RPP RS SD SHM SIO SPN SS TCT TPI TPP TPS TSA TSH TSP TSS TYM UP UU XSI ([XBD 1.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_08_01)). `_POSIX_THREADS` and `_POSIX_REALTIME_SIGNALS` are mandatory.
4. **XSI is optional.** "The system may support the X/Open System Interfaces (XSI) option" ([XBD 2.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_01)). An XSI system must also support the options FSC, TSA, TSS and TSH ([XBD 2.1.4.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_04)).
5. **`AF_INET` is mandatory.** Base conformance requires IPv4 Internet-domain sockets, so it requires an IPv4 protocol stack with TCP as the default stream protocol and UDP as the default datagram protocol. IPv6 (IP6) and raw sockets (RS) are optional. Citations are in the next section.

## The `AF_INET` / TCP/IP question

**Verdict: yes.** POSIX.1-2024 base conformance (without XSI and without any option) requires working `AF_INET` sockets.

The evidence, all in XSH 2.10 Sockets ([XSH 2.10](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10)) and the base headers:

- **IPv4 sockets are mandatory, stated outright.** XSH 2.10.19, "Use of Sockets over Internet Protocols Based on IPv4": "Support for sockets over Internet protocols based on IPv4 is mandatory. IPv4 is described in RFC 791." ([XSH 2.10.19](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_19)). The section has no margin code.
- **UNIX domain sockets are mandatory too.** XSH 2.10.17: "Support for UNIX domain sockets is mandatory." ([XSH 2.10.17](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_17)).
- **TCP and UDP are the defaults.** XSH 2.10.18: "When a socket is created in the Internet family with a protocol value of zero, the implementation shall use the protocol listed below": `SOCK_STREAM` → `IPPROTO_TCP`, `SOCK_DGRAM` → `IPPROTO_UDP`, `SOCK_RAW` → `IPPROTO_RAW` (RS-marked), `SOCK_SEQPACKET` → unspecified ([XSH 2.10.18](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_18)).
- **The headers are unmarked (base):**
  - [`<sys/socket.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_socket.h.html) defines `AF_INET`, `AF_UNIX`, `AF_UNSPEC` without a margin code. Only `AF_INET6` carries `[IP6]` and only `SOCK_RAW` carries `[RS]`.
  - [`<netinet/in.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/netinet_in.h.html) defines `sockaddr_in`, `in_addr`, `INADDR_ANY`, `INADDR_BROADCAST`, `INET_ADDRSTRLEN`, and the protocol constants `IPPROTO_IP`, `IPPROTO_ICMP`, `IPPROTO_TCP` and `IPPROTO_UDP`, all unmarked. `IPPROTO_IPV6` is `[IP6]` and `IPPROTO_RAW` is `[RS]`.
  - [`<netinet/tcp.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/netinet_tcp.h.html) (base) defines `TCP_NODELAY`, though "the implementation need not allow the value of the option to be set via setsockopt() or retrieved via getsockopt()".
  - [`<net/if.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/net_if.h.html) (base) declares `if_nameindex()`, `if_nametoindex()`, `if_indextoname()` and `if_freenameindex()`.
- **Options.** `_POSIX_IPV6` [IP6] and `_POSIX_RAW_SOCKETS` [RS] appear in the list of constants a system "may support" ([XBD 2.1.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_03)). XSH 2.10.20 (IPv6) applies only "on implementations that support the IPV6 option" ([XSH 2.10.20](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_20)).

Points the standard leaves open, which affect how much stack "mandatory IPv4" implies:

- **No extra protocol is named.** No text beyond the default-protocol rule above requires a particular transport. `socket()` may fail with `[EPROTONOSUPPORT]` when "the protocol is not supported by the implementation" ([socket()](https://pubs.opengroup.org/onlinepubs/9799919799/functions/socket.html)). XSH 2.10.1 says "It is not required that an address family support all socket types" ([XSH 2.10.1](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_01)).
- **No physical interface is required.** XSH 2.10.5 says a network interface "usually has a hardware device associated with it, though certain interfaces such as the loopback interface, do not" ([XSH 2.10.5](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_05)). XSH 2.10.4 says "a routing information database is maintained" ([XSH 2.10.4](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_04)). `INADDR_LOOPBACK` is not in POSIX: the `<netinet/in.h>` rationale names it as an extension many implementations have.
- **No rationale is given.** XRAT B.2.10.19 says "There is no additional rationale provided for this section" ([XRAT B.2.10.19](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html#tag_22_02_10_19)).
- **Name resolution is libc's job.** `getaddrinfo()` and the rest of [`<netdb.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/netdb.h.html) are base, but they need only sockets and files from the kernel.

## How POSIX.1-2024 partitions requirements

- **Mandatory (base).** Everything unmarked or `[CX]`, plus the 15 former options pinned to `202405L` and the four pinned to values greater than zero (headline 2). `_POSIX_CHOWN_RESTRICTED` and `_POSIX_NO_TRUNC` must be defined with a value other than -1 ([XBD 2.1.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_03)).
- **Options.** ADV CPT DC FSC IP6 ML MLR MSG PIO PS RS SHM SPN SS SIO TSA TSS TCT TPI TPP RPI RPP TPS TSH TSP TYM. Each has a `<unistd.h>` constant that is -1/undefined (not supported), 0 (decided at runtime) or `202405L` (always supported) ([XBD 2.1.6](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_06); [`<unistd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html)). "When an implementation claims that an option is supported, all of its constituent parts shall be provided" ([XBD 2.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_01)).
- **XSI option.** Functions and text marked `[XSI]`. Within XSI there are Option Groups ([XBD 2.1.5.2](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_05)):
  - Encryption (`_XOPEN_CRYPT`).
  - Realtime (`_XOPEN_REALTIME`), which requires ML, MLR, MSG, PS, SHM and SIO, plus FSC; PIO stays optional.
  - Advanced Realtime: ADV, CPT, SPN, SS and TYM.
  - Realtime Threads (`_XOPEN_REALTIME_THREADS`): TPI, TPP, TPS, RPI and RPP.
  - Advanced Realtime Threads: TCT and TSP.
- **Obsolescent (`[OB]`).** Still required where unmarked otherwise, but Strictly Conforming applications "shall not use" it ([XBD 1.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_08_01)).

## Classification basis (kernel-facing vs libc)

The standard draws no kernel/libc line (headline 1), and the rationale shows that the split is the implementer's choice:

- Semaphores "using test-and-set instructions on shared memory locations", where the library routine "will issue a blocking semaphore system call" only when it must block ([XRAT B.2.8](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html#tag_22_02_08)).
- `read()` either "as a system call" or with "parts of read() at user level" (XRAT B, Threads rationale).
- `posix_spawn()` given as an "Example posix_spawn() library routine" built on `fork()`/`exec` ([XRAT B.3.3](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html#tag_22_03_03)).
- A precedent outside POSIX: on Linux, "The current Linux POSIX AIO implementation is provided in user space by glibc" ([aio(7)](https://man7.org/linux/man-pages/man7/aio.7.html)).

In the inventory below, **kernel-facing** means the facility needs one of the following, which unprivileged user code in one process cannot provide alone:

- state that outlives a process or is shared between processes (open file descriptions, the file system, process and session tables, credentials, IPC objects);
- control of address spaces;
- asynchronous delivery into another execution context (signals);
- a hardware source (clocks, timers, devices, entropy, the network).

Some mandatory interfaces can be built by a libc on top of other kernel primitives. Those are listed in each area's last column, so the kernel's minimum can be read off.

## Area inventory

Column key:

- **Base (mandatory)**: kernel-facing interfaces and semantics required of every conforming system.
- **Optional**: marked items, by option code.
- **libc-layer**: mandatory items in the area that a libc can implement on the kernel primitives in the Base column.

Header links go to the per-header page under `basedefs/`.

### 1. Processes and exec

- **Base:** `fork`, `_Fork` (added in Issue 8), `execve`, `fexecve`, `_exit`, `wait`, `waitpid`, `waitid`, `getpid`, `getppid`. Process groups and sessions: `setpgid`, `getpgid`, `getpgrp`, `setsid`, `getsid`. Also `kill`, `alarm`, `pause`, `times`, `uname`, `gethostname`, `chdir`/`fchdir`, `getcwd`, `umask` ([`<unistd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html), [`<sys/wait.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_wait.h.html), [`<sys/times.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_times.h.html), [`<sys/utsname.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_utsname.h.html)). `sched_yield` ([`<sched.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sched.h.html)).
- **Optional:**
  - **SPN:** all of [`<spawn.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/spawn.h.html) (`posix_spawn`, `posix_spawnp`, file actions, attributes).
  - **PS:** `sched_setscheduler`, `sched_getscheduler`, `sched_setparam`, `sched_getparam`, `SCHED_FIFO`/`SCHED_RR`. `sched_get_priority_max`/`min` and `sched_rr_get_interval` are PS|TPS.
  - **SS:** `SCHED_SPORADIC`.
  - **XSI:** `nice`, `getpriority`, `setpriority`, `getrusage`, `gethostid`, `WCONTINUED`/`WIFCONTINUED`.
- **libc-layer:** the `exec*` family other than `execve`/`fexecve`; `posix_spawn` (XRAT B.3.3); `wait`/`waitpid` over `waitid` (implementation choice).
- **Not in POSIX.1-2024:** `vfork` (404).

### 2. Signals and job control

- **Base:**
  - `sigaction` with `SA_SIGINFO`, `SA_RESTART`, `SA_RESETHAND`, `SA_NODEFER` and `SA_NOCLDSTOP`.
  - `sigprocmask`, `pthread_sigmask`, `pthread_kill`, `sigpending`, `sigsuspend`, `sigwait`, `sigwaitinfo`, `sigtimedwait`, `sigqueue`.
  - `siginfo_t` with `si_code`, `si_pid`, `si_uid`, `si_addr`, `si_status`, `si_value`.
  - Realtime signals `SIGRTMIN`..`SIGRTMAX` (`_POSIX_REALTIME_SIGNALS` mandatory; `{_POSIX_RTSIG_MAX}` ≥ 8, `{_POSIX_SIGQUEUE_MAX}` ≥ 32).
  - Signals `SIGABRT` through `SIGUSR2`, plus `SIGWINCH` (added in Issue 8) and `SIGURG`. All listed with `[CX]` or no mark in [`<signal.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/signal.h.html).
  - Job control (`_POSIX_JOB_CONTROL` > 0): `SIGTSTP`, `SIGTTIN`, `SIGTTOU`, `SIGCONT`, `SIGSTOP`, `tcsetpgrp`, `tcgetpgrp`, `tcgetsid`, plus the semantics in XSH 2.4 Signal Concepts ([XSH 2.4](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_04)).
  - `SIGPIPE`, and `MSG_NOSIGNAL` on sockets.
- **Optional (XSI):**
  - `sigaltstack`, `SA_ONSTACK`, `SS_ONSTACK`/`SS_DISABLE`, `MINSIGSTKSZ`/`SIGSTKSZ`.
  - `SA_NOCLDWAIT`, `killpg`, `si_errno`.
  - Signals `SIGSYS`, `SIGTRAP`, `SIGVTALRM`, `SIGXCPU`, `SIGXFSZ`.
- **libc-layer:** `raise`, `signal`, `sigset` manipulation (`sigemptyset` …), `psignal`, `psiginfo`, `sig2str`/`str2sig`; `killpg` over `kill`.
- **Not in POSIX.1-2024:** `SIGPOLL` and `SIGPROF` (they appear only in change history), `getcontext`/`ucontext` functions (404).

### 3. Terminals and pseudo-terminals

- **Base:**
  - The whole General Terminal Interface ([XBD 11](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap11.html)): controlling terminal, foreground/background process groups, canonical and non-canonical input, special characters, modem disconnect.
  - [`<termios.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/termios.h.html): `tcgetattr`, `tcsetattr`, `tcdrain`, `tcflow`, `tcflush`, `tcsendbreak`, `tcgetsid`, `cf[gs]et[io]speed`, `tcgetwinsize`/`tcsetwinsize` (added in Issue 8).
  - `O_TTY_INIT` and `O_NOCTTY` ([`<fcntl.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/fcntl.h.html)).
  - The files `/dev/tty` and `/dev/console`; `/dev/console` "shall provide an interface to the system console conforming to the requirements of 11. General Terminal Interface" ([XBD 10.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap10.html#tag_10_01)).
- **Optional (XSI):**
  - Pseudo-terminals: `posix_openpt`, `grantpt`, `unlockpt`, `ptsname`, `ptsname_r` ([`<stdlib.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/stdlib.h.html)).
  - termios output flags `ONLCR`, `OCRNL`, `ONOCR`, `ONLRET`, `OFILL`, `OFDEL`, and the delay masks `NLDLY`, `CRDLY`, `TABDLY`, `BSDLY`, `VTDLY`, `FFDLY`.
- **libc-layer:** `isatty`, `ttyname`/`ttyname_r`, `ctermid`, `cf*speed` (fields of `termios`).
- **Not in POSIX.1-2024:** `ioctl` (404; `<stropts.h>` 404).

### 4. Files, directories, permissions, I/O multiplexing

- **Base:**
  - `open`/`openat` (including `O_CLOEXEC`, `O_CLOFORK` (added in Issue 8), `O_DIRECTORY`, `O_NOFOLLOW`, `O_EXEC`, `O_SEARCH`, `O_NONBLOCK`, `O_APPEND`, `O_SYNC`), `creat`, `close`, `posix_close`.
  - `read`, `write`, `pread`, `pwrite`, `lseek`, `ftruncate`, `truncate`.
  - `dup`, `dup2`, `dup3`, `pipe`, `pipe2`, `fcntl` (`F_DUPFD_CLOFORK`, `FD_CLOFORK`, `F_GETOWN_EX`/`F_SETOWN_EX`).
  - `stat`, `fstat`, `lstat`, `fstatat`, `chmod`, `fchmod`, `fchmodat`, `chown`, `fchown`, `fchownat`, `lchown`, `access`, `faccessat`.
  - `link`, `linkat`, `symlink`, `symlinkat`, `readlink`, `readlinkat`, `unlink`, `unlinkat`, `rename`, `renameat`, `mkdir`, `mkdirat`, `rmdir`, `mkfifo`, `mkfifoat`, `utimensat`, `futimens`.
  - `statvfs`/`fstatvfs` ([`<sys/statvfs.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_statvfs.h.html)) and `posix_getdents` (added in Issue 8; [`<dirent.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/dirent.h.html)).
  - `select`, `pselect` ([`<sys/select.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_select.h.html)), `poll`, `ppoll` ([`<poll.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/poll.h.html)).
  - Large-file support (XCU) ([XBD 2.1.3.2](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_03)).
  - Required directories and files `/`, `/dev`, `/tmp`, `/dev/null` ([XBD 10.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap10.html#tag_10_01)).
  - `_POSIX_CHOWN_RESTRICTED` and `_POSIX_NO_TRUNC` ≠ -1.
- **Optional:**
  - **FSC:** `fsync`.
  - **SIO:** `fdatasync`, `O_DSYNC`, `O_RSYNC`.
  - **ADV:** `posix_fadvise`, `posix_fallocate`.
  - **DC:** `posix_devctl` ([`<devctl.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/devctl.h.html), added in Issue 8).
  - **XSI:**
    - `readv`/`writev` (all of [`<sys/uio.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_uio.h.html) is XSI).
    - `mknod`/`mknodat`, `sync`, `utimes` ([`<sys/time.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_time.h.html) is XSI), `seekdir`/`telldir`.
    - In [`<sys/stat.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_stat.h.html): `S_ISVTX`, the `S_IF*` type constants (the `S_IS*()` macros are base), and `st_rdev`, `st_blksize`, `st_blocks`.
- **libc-layer:** `opendir`/`readdir`/`closedir`/`scandir`/`fdopendir` over `posix_getdents`; `creat` over `open`; `select` over `pselect`/`poll` (implementation choice); `remove`; stdio.
- **Not in POSIX.1-2024:** `utime()`/`<utime.h>` (404), `ioctl` (404), `gettimeofday` (see area 8).

### 5. File locking

- **Base:** process-owned record locks via `fcntl` `F_GETLK`/`F_SETLK`/`F_SETLKW`. Open-file-description–owned locks `F_OFD_GETLK`/`F_OFD_SETLK`/`F_OFD_SETLKW`, added in Issue 8 (Austin Group Defect 768; [`<fcntl.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/fcntl.h.html), [fcntl()](https://pubs.opengroup.org/onlinepubs/9799919799/functions/fcntl.html)).
- **Optional (XSI):** `lockf`.
- **libc-layer:** `lockf` over `fcntl` locks.
- **Not in POSIX.1-2024:** `flock` (404).

### 6. Memory mapping and protection

- **Base:** `mmap`, `munmap`, `mprotect` (`_POSIX_MAPPED_FILES` and `_POSIX_MEMORY_PROTECTION` mandatory). `MAP_SHARED`, `MAP_PRIVATE`, `MAP_FIXED`, `MAP_ANONYMOUS`/`MAP_ANON` (the last two added in Issue 8 by Defect 850) ([`<sys/mman.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_mman.h.html)).
- **Optional:**
  - **ML:** `mlockall`, `munlockall`.
  - **MLR:** `mlock`, `munlock`.
  - **SHM:** `shm_open`, `shm_unlink`.
  - **TYM:** `posix_typed_mem_open`, `posix_typed_mem_get_info`, `posix_mem_offset`.
  - **ADV:** `posix_madvise`.
  - **XSI|SIO:** `msync`.
- **libc-layer:** `malloc` family, `posix_memalign` (ADV) over `mmap`; `dlopen`/`dlsym` (base, [`<dlfcn.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/dlfcn.h.html)) over `open` and `mmap`.

### 7. Threads and synchronisation primitives

- **Base** (from [`<pthread.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/pthread.h.html), [`<semaphore.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/semaphore.h.html) and [XSH 2.9](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_09)):
  - Threads (`_POSIX_THREADS`): `pthread_create`, `pthread_exit`, `pthread_join`, `pthread_detach`, cancellation.
  - Mutexes, including robust mutexes (`pthread_mutexattr_setrobust`, `pthread_mutex_consistent`), condition variables, rwlocks, barriers, spin locks.
  - Timed and clock waits: `pthread_mutex_timedlock`, `pthread_mutex_clocklock`, `pthread_cond_clockwait` (added in Issue 8), `pthread_rwlock_clock*`.
  - Per-thread signal masks and `pthread_kill`.
  - Semaphores (`_POSIX_SEMAPHORES` mandatory): unnamed `sem_init` and named `sem_open`/`sem_unlink`, `sem_clockwait`.
  - Kernel-facing parts: creating schedulable execution contexts; a block/wake mechanism for contended sync objects (XRAT B.2.8 describes the "blocking semaphore system call" pattern); per-thread signal delivery; named-semaphore namespace.
- **Optional:**
  - **TSH:** process-shared mutexes, condvars, rwlocks and barriers (`*_setpshared`); required by XSI.
  - **TPS:** thread scheduling (`pthread_setschedparam`, `pthread_attr_setscope`, `pthread_setschedprio`, …).
  - **TPI, TPP, RPI, RPP (MC1):** mutex priority inheritance and protection (`pthread_mutexattr_setprotocol`, `*prioceiling`).
  - **TCT:** `pthread_getcpuclockid`.
  - **TSP:** thread sporadic server.
  - **TSA/TSS:** `pthread_attr_setstack`/`setstacksize`; required by XSI.
- **libc-layer:** thread-specific data (`pthread_key_*`), `pthread_once`, attribute objects, cleanup handlers, uncontended fast paths of mutexes and semaphores (XRAT B.2.8), and TSA/TSS stack attributes.

### 8. Time and clocks

- **Base:**
  - `CLOCK_REALTIME`; `CLOCK_MONOTONIC` (mandatory per Austin Group Defect 1346, noted on [`<unistd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html)).
  - `clock_gettime`, `clock_settime`, `clock_getres`, `clock_nanosleep` (`_POSIX_CLOCK_SELECTION`), `nanosleep`.
  - Per-process timers `timer_create`, `timer_settime`, `timer_gettime`, `timer_getoverrun`, `timer_delete` (`_POSIX_TIMERS`), with `sigevent` notification.
  - `alarm`, `time`, `times`, `timespec_get` ([`<time.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/time.h.html)).
  - `time_t` must have a width of at least 64 bits (Defect 1462, [`<sys/types.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_types.h.html)).
  - `{_POSIX_CLOCKRES_MIN}` = 20 000 000 ns ([`<limits.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/limits.h.html)).
- **Optional:**
  - **CPT:** `CLOCK_PROCESS_CPUTIME_ID`, `clock_getcpuclockid`.
  - **TCT:** `CLOCK_THREAD_CPUTIME_ID`.
- **libc-layer:** `time`, `timespec_get` over `clock_gettime`; `sleep` over `nanosleep`; `SIGEV_THREAD` notification (thread creation in libc); calendar and time-zone functions.
- **Not in POSIX.1-2024:** `gettimeofday`, `getitimer`, `setitimer` (404; [`<sys/time.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_time.h.html) records "Austin Group Defect 1330 is applied, removing obsolescent interfaces").

### 9. Sockets and networking

- **Base:**
  - All of [`<sys/socket.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_socket.h.html): `socket`, `socketpair`, `bind`, `listen`, `accept`, `accept4`, `connect`, `send`, `sendto`, `sendmsg`, `recv`, `recvfrom`, `recvmsg`, `getsockopt`, `setsockopt`, `shutdown`, `sockatmark`, `getpeername`, `getsockname`.
  - Socket types `SOCK_STREAM`, `SOCK_DGRAM`, `SOCK_SEQPACKET`; flags `SOCK_NONBLOCK`, `SOCK_CLOEXEC`, `SOCK_CLOFORK`, `MSG_CMSG_CLOEXEC`/`CLOFORK`, `MSG_NOSIGNAL`; `SCM_RIGHTS` descriptor passing; `SO_DOMAIN`/`SO_PROTOCOL`.
  - Address families **`AF_UNIX` (mandatory)** and **`AF_INET` (mandatory; TCP/UDP defaults)**. Full detail and citations are in the AF_INET section above.
  - `<netinet/in.h>`, `<netinet/tcp.h>`, `<net/if.h>`, `<sys/un.h>`.
  - Socket semantics in XSH 2.10.1–2.10.16: non-blocking mode, owner and `SIGURG`, pending errors, out-of-band data, connection queue, options ([XSH 2.10](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10)).
- **Optional:**
  - **IP6:** `AF_INET6`, `sockaddr_in6`, `IPPROTO_IPV6`, IPv6 options, "use of AF_INET6 sockets over IPv4" ([XRAT B.2.10.20](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html#tag_22_02_10_20)).
  - **RS:** `SOCK_RAW`, `IPPROTO_RAW`; creating a raw socket "shall require appropriate privileges" ([XSH 2.10.6](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_10_06)).
- **libc-layer:** [`<netdb.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/netdb.h.html) (`getaddrinfo`, `getnameinfo`, …), [`<arpa/inet.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/arpa_inet.h.html) (`inet_pton`, `htonl`, …), and `if_nameindex` (if the kernel exposes the interface list by some other means).

### 10. IPC (other than sockets and signals)

- **Base:** pipes (`pipe`, `pipe2`), FIFOs (`mkfifo`), `MAP_SHARED` mappings, named semaphores (area 7).
- **Optional:**
  - **MSG:** POSIX message queues, all of [`<mqueue.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/mqueue.h.html) (`mq_open`, `mq_send`, `mq_receive`, `mq_notify`, `mq_timed*`, …).
  - **SHM:** `shm_open`/`shm_unlink`.
  - **XSI:** XSI IPC ([XSH 2.7](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_07)): `msgget`, `msgsnd`, `msgrcv`, `msgctl` ([`<sys/msg.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_msg.h.html)); `semget`, `semop`, `semctl` ([`<sys/sem.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_sem.h.html)); `shmget`, `shmat`, `shmdt`, `shmctl` ([`<sys/shm.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_shm.h.html)); `ftok` ([`<sys/ipc.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_ipc.h.html)).
- **libc-layer:** `popen`/`pclose`, `system` (over `fork`/`exec`/`pipe`); `ftok` (over `stat`).

### 11. Users, groups, credentials

- **Base:** `getuid`, `geteuid`, `getgid`, `getegid`, `setuid`, `setgid`, `seteuid`, `setegid`, `getgroups`. Saved set-user-ID and set-group-ID (`_POSIX_SAVED_IDS` > 0). Set-ID-on-exec semantics. "Appropriate privileges" checks. `_POSIX_CHOWN_RESTRICTED` ([`<unistd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html)). `{NGROUPS_MAX}` ≥ 8.
- **Optional (XSI):** `setreuid`, `setregid`, and `getresuid`, `getresgid`, `setresuid`, `setresgid` (the last four added in Issue 8, Defects 1344/1666).
- **libc-layer:** [`<pwd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/pwd.h.html) and [`<grp.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/grp.h.html) database lookups, `getlogin`; XSI [`<utmpx.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/utmpx.h.html) (`getutxent` …).
- **Not in POSIX.1-2024:** `setgroups` (404).

### 12. Resource limits and accounting

- **Base:** `getrlimit`/`setrlimit` with `RLIMIT_CORE`, `RLIMIT_DATA`, `RLIMIT_FSIZE`, `RLIMIT_NOFILE`, `RLIMIT_STACK`, `RLIMIT_AS`, `RLIM_INFINITY`, `RLIM_SAVED_*` ([`<sys/resource.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/sys_resource.h.html)). `times()`. Runtime limit values reported by `sysconf`/`pathconf`/`fpathconf`, which the conformance document must describe ([XBD 2.1.2](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_02)).
- **Optional (XSI):** `RLIMIT_CPU`, `getrusage`, `getpriority`, `setpriority`, `nice`.
- **libc-layer:** `sysconf`/`pathconf` once the kernel exposes the values; `nice` over `setpriority`.

### 13. Asynchronous and prioritised I/O

- **Base:** `aio_read`, `aio_write`, `aio_error`, `aio_return`, `aio_cancel`, `aio_suspend`, `lio_listio` (`_POSIX_ASYNCHRONOUS_IO` mandatory; [`<aio.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/aio.h.html)). `{_POSIX_AIO_MAX}` ≥ 1, `{_POSIX_AIO_LISTIO_MAX}` ≥ 2.
- **Optional:** `aio_fsync` (FSC|SIO); **PIO** request priorities.
- **libc-layer:** the whole of AIO can be a user-space library over threads and `pread`/`pwrite` (precedent: glibc, [aio(7)](https://man7.org/linux/man-pages/man7/aio.7.html)).

### 14. Anything else

- **Entropy (base):** `getentropy` (added in Issue 8; [getentropy()](https://pubs.opengroup.org/onlinepubs/9799919799/functions/getentropy.html)) needs a kernel or hardware randomness source.
- **Devices (base):** `/dev/null`, `/dev/tty`, `/dev/console` ([XBD 10.1](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap10.html#tag_10_01)).
- **Device control (DC option):** `posix_devctl`.
- **Error numbers (base):** the `errno` values and their meanings in [XSH 2.3](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_03).
- **Programming environments:** the `_POSIX_V8_*` constants on [`<unistd.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/unistd.h.html) name the C environments a system provides (`ILP32_OFF32`, `ILP32_OFFBIG`, `LP64_OFF64`, `LPBIG_OFFBIG`). The standard "does not make any attempt to define application binary interaction with the underlying operating system", so the Syscall ABI is Nova's own.
- **Shell and utilities (XCU):** these are mandatory for conformance ([XBD 2.1.3.2](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap02.html#tag_02_01_03)) but are userspace. They reach the kernel only through the XSH interfaces above. They are not inventoried here.

## Minimum limits a base system must meet (kernel-relevant subset)

From [`<limits.h>`](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/limits.h.html), "Minimum Values" (the smallest value an implementation may report):

| Limit | Minimum | Limit | Minimum |
| --- | --- | --- | --- |
| `_POSIX_ARG_MAX` | 4096 | `_POSIX_OPEN_MAX` | 20 |
| `_POSIX_CHILD_MAX` | 25 | `_POSIX_PATH_MAX` | 256 |
| `_POSIX_LINK_MAX` | 8 | `_POSIX_PIPE_BUF` | 512 |
| `_POSIX_MAX_CANON` | 255 | `_POSIX_RTSIG_MAX` | 8 |
| `_POSIX_MAX_INPUT` | 255 | `_POSIX_SIGQUEUE_MAX` | 32 |
| `_POSIX_NAME_MAX` | 14 | `_POSIX_SYMLOOP_MAX` | 8 |
| `_POSIX_NGROUPS_MAX` | 8 | `_POSIX_TIMER_MAX` | 32 |
| `_POSIX_HOST_NAME_MAX` | 255 | `_POSIX_THREAD_THREADS_MAX` | 64 |
| `_POSIX_SEM_NSEMS_MAX` | 256 | `_POSIX_SEM_VALUE_MAX` | 32767 |
| `_POSIX_TTY_NAME_MAX` | 9 | `_POSIX_CLOCKRES_MIN` | 20 000 000 ns (a maximum resolution) |

XSI raises some of these: `_XOPEN_NAME_MAX` 255, `_XOPEN_PATH_MAX` 1024, `_XOPEN_IOV_MAX` 16.

## Summary: mandatory vs optional, by area

| Area | Mandatory kernel-facing core | Options that add kernel surface |
| --- | --- | --- |
| Processes and exec | fork/_Fork, execve/fexecve, wait*, pgrp/session, kill, times, uname | SPN, PS, SS, XSI (nice, priorities, rusage) |
| Signals and job control | sigaction, masks, sigqueue + RT signals, sigwait*, job control | XSI (sigaltstack, SA_NOCLDWAIT, SIGSYS/TRAP/VTALRM/XCPU/XFSZ) |
| Terminals and ptys | XBD 11 line discipline, termios, winsize, /dev/tty, /dev/console | XSI (all pseudo-terminal functions, output delays) |
| Files, dirs, permissions, polling | open/at-family, fd ops incl. CLOFORK, stat, links, statvfs, posix_getdents, select/poll | FSC, SIO, ADV, DC, XSI (readv/writev, mknod, sync, st_blocks) |
| File locking | fcntl process locks and OFD locks | XSI (lockf) |
| Memory mapping | mmap/munmap/mprotect, MAP_ANONYMOUS | ML, MLR, SHM, TYM, ADV, XSI\|SIO (msync) |
| Threads and sync | threads, block/wake for mutex/cond/rwlock/barrier/sem, robust mutexes, named semaphores | TSH, TPS, TPI/TPP/RPI/RPP, TCT, TSP |
| Time and clocks | REALTIME + MONOTONIC clocks, clock_nanosleep, POSIX timers, 64-bit time_t | CPT, TCT |
| Sockets and networking | AF_UNIX, **AF_INET (TCP/UDP)**, full sockets API, SCM_RIGHTS | IP6, RS |
| IPC | pipes, FIFOs, shared mappings | MSG, SHM, XSI (msg/sem/shm) |
| Credentials | real/effective/saved IDs, supplementary groups, privileges | XSI (setre*/setres*/getres*) |
| Resource limits | getrlimit/setrlimit (6 resources), sysconf values | XSI (RLIMIT_CPU, getrusage, priorities) |
| Async I/O | (aio mandatory, but implementable in libc) | PIO, FSC\|SIO |
| Other | getentropy, /dev/null, errno semantics | DC |

## Open points (not settled by the sources read)

- **How much of TCP must work.** The standard mandates IPv4 sockets and names TCP/UDP as the default protocols. It does not spell out a protocol-conformance level, which RFCs beyond RFC 791 apply, or whether a non-loopback interface must exist. That has to be judged from the per-function pages (`connect`, `listen`, `accept`, `send`, …), which were not read line by line here.
- **The kernel/libc split is an analysis.** POSIX explicitly declines to draw it, so the "libc-layer" column is an analysis of implementability, not a standard requirement.
