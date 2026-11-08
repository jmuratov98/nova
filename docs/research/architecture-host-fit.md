# Architecture fit for an Apple M4 host

Research for [#2](https://github.com/jmuratov98/nova/issues/2) ("Which architecture suits an Apple M4 host best?"), part of the map [#1](https://github.com/jmuratov98/nova/issues/1). It gathers the facts the architecture decision for the **First process tree** depends on. It does **not** make the decision, which belongs to a separate human-in-the-loop ticket.

- **Date:** 2026-11-08
- **Host:** Apple M4, macOS 15.6 (24G84), arm64
- **Tools found on the host:** Apple clang 17.0.0 (clang-1700.0.13.5), Apple lldb-1700.0.9.502, Homebrew QEMU 11.1.2, Homebrew `lld` 23.1.4, Homebrew `llvm` 23.1.4 (keg-only), Homebrew `x86_64-elf-gdb` 18.1
- **Method:** read-only local checks plus small bare-metal test kernels run under QEMU from the scratchpad (see [Appendix A](#appendix-a-how-the-local-measurements-were-made)), and primary sources (QEMU source and docs at tag `v11.1.2`, Homebrew formulae, LLVM, the Limine protocol, the Intel SDM, the RISC-V specifications, and the xv6 repositories). Every claim cites a source from the [Sources](#sources) list. Anything not confirmed from a primary source is marked **unconfirmed**.

## Summary

| | x86_64 | AArch64 | RISC-V (riscv64) |
|---|---|---|---|
| QEMU accelerator on this host | TCG only [L1][Q1] | **HVF** or TCG [L1][Q1] | TCG only [L1][Q1] |
| Launch to edk2 UEFI shell, no boot-menu wait | 1.15 s (TCG) [L5] | 0.11 s (HVF), 0.42 s (TCG) [L5] | 0.97 s (TCG) [L5] |
| Bare-metal kernel startup (QEMU launch to power-off) | ~0.05 s [L4] | ~0.025 s [L4] | ~0.04 s [L4] |
| gdbstub: breakpoints, stepping, hardware breakpoints, watchpoints | all work (TCG) [L6] | all work under HVF and TCG [L6][Q3] | all work (TCG) [L6] |
| Apple lldb drives QEMU's gdbstub | yes [L6] | yes [L6] | yes [L6] |
| Cross-gdb with an `arm64_sequoia` bottle | `x86_64-elf-gdb` (installed) [B2] | `aarch64-elf-gdb` [B3] | `riscv64-elf-gdb` [B4] |
| Apple clang 17 emits ELF objects | yes [L2] | yes [L2] | **no backend** [L2] |
| Links with `ld.lld` | yes [L3] | yes [L3] | yes [L3] |
| Limine firmware paths | BIOS and UEFI [M1][M3] | UEFI only [M1] | UEFI only [M1] |
| MIT xv6 | 32-bit x86 only, no longer maintained [X2] | none from MIT [X4] | maintained, with a book [X1][X3] |

## 1. QEMU on Apple silicon

### 1.1 Which accelerator each guest can use

- QEMU's build only enables HVF for the guest that matches the host CPU. On an `aarch64` host, `CONFIG_HVF` is built for `aarch64-softmmu` only; `x86_64-softmmu` gets HVF only on an `x86_64` host [Q1]. QEMU's docs list HVF host architectures as "x86, Arm" and describe TCG as "purely emulated" [Q2].
- On this host, `qemu-system-aarch64 -accel help` lists `hvf` and `tcg`, while `qemu-system-x86_64` and `qemu-system-riscv64` list only `tcg` [L1].
- Under HVF the CPU model is the host's: the `virt` docs list `host` as "with KVM and HVF only", and `max` as "same as `host` for KVM and HVF" [Q8].

### 1.2 How fast each boots (measured on this M4)

These are indicative measurements of tiny test kernels and firmware, not of a Limine-booted kernel. Each figure covers 3 runs. The method is in [Appendix A](#appendix-a-how-the-local-measurements-were-made).

| Scenario | AArch64 HVF | AArch64 TCG | riscv64 TCG | x86_64 TCG |
|---|---|---|---|---|
| Launch, print to serial, power off (no loop) | 0.025 s | 0.025–0.033 s | 0.040–0.041 s (includes OpenSBI) | 0.052–0.053 s (SeaBIOS + Multiboot; one first-run outlier at 0.084 s) |
| Same plus a 10⁸-iteration load/add/store loop | 0.051–0.061 s | 0.189–0.199 s | 0.163–0.170 s | 0.170–0.173 s |
| Loop cost alone (approx.) | ~0.03 s | ~0.17 s | ~0.12 s | ~0.12 s |
| Launch to edk2 "UEFI Interactive Shell", `-boot menu=on,splash-time=0` | 0.11 s | 0.42 s | 0.97–0.98 s | 1.15–1.16 s (OVMF, `q35`) |
| Same, with the firmware's default boot-menu wait | 5.12 s | 5.44–5.59 s | 5.99–6.04 s | 1.15–1.22 s |

Observations [L4][L5]:

- With no firmware, all three start a kernel in tens of milliseconds, so QEMU start-up dominates and the accelerator barely matters.
- On a simple CPU-bound loop, TCG was roughly 4–6× slower than HVF. ISAs differ in instruction count per iteration, so the cross-architecture TCG numbers are only rough.
- The edk2 builds Homebrew QEMU ships (`edk2-stable202408`) for AArch64 and riscv64 wait about 5 s in the boot manager (`[Bds]BdsWait(4)..Zzzz...`) unless `-boot menu=on,splash-time=0` is passed. The x86_64 OVMF build did not wait. Without the wait, edk2 reaches its shell in 0.11 s on HVF.
- **TCG pitfall:** the first test kernels kept the loop's variable on the same 4 KiB page as the code. Under TCG, the 10⁸-iteration loop then took 19.5–23.8 s instead of about 0.2 s. The page-aligned rerun showed the slowdown came from that layout; under HVF the same layout ran in 0.05 s. The cause is consistent with TCG's self-modifying-code handling, but that is inferred, not read from QEMU source. Keeping writable data off code pages avoids it.
- Not measured: Limine's own boot time, and a full Limine boot on each target (**unconfirmed**). Limine's `timeout: 0` boots the selected entry without showing the menu [M5].

### 1.3 HVF limitations that matter for kernel work (AArch64 only)

- **gdbstub support exists.** It arrived with commit `eb2edc42b126` "hvf: add guest debugging handlers for Apple Silicon hosts" (2023-06-06), first shipped in QEMU 8.1.0 [Q4]. The v11.1.2 code handles software-step, `BRK` software breakpoints, hardware breakpoints, and hardware watchpoints (`EC_SOFTWARESTEP`, `EC_AA64_BKPT`, `EC_BREAKPOINT`, `EC_WATCHPOINT`) [Q3]. It implements single-step through `MDSCR_EL1.SS`/`PSTATE.SS` and honours QEMU's `SSTEP_NOIRQ` step flag [Q3]. Live tests confirmed all of these with lldb ([section 2](#2-debugging)) [L6].
- **The host caps hardware breakpoints and watchpoints.** QEMU reads the counts from the host's `ID_AA64DFR0_EL1` (`BRPs + 1`, `WRPs + 1`) [Q3]. On this M4 the guest sees `ID_AA64DFR0_EL1 = 0x10305106`, which decodes to **6 hardware breakpoints and 4 watchpoints** [L6]. Under TCG, QEMU advertises an unlimited number of both [Q7].
- **The interrupt controller differs by accelerator.** From the `virt-11.1` machine type (QEMU 11.1), HVF defaults to Apple's in-kernel vGIC: `kernel-irqchip` is on unless the machine type is 11.0 or older [Q5][Q6]. The vGIC needs macOS 15 [Q3]. With it, QEMU offers only GICv3 and rejects the ITS ("ITS not supported on HVF when using the hardware vGIC") [Q5]. With no `gic-version` given, TCG defaults to **GICv2** when there are 8 CPUs or fewer [Q5]. A kernel tested under both HVF and TCG (as on Linux CI) therefore needs `gic-version=3` everywhere or support for both GIC versions. The vGIC commits (`5a2a13bc7a03`, `d7a75ea483a5`, 2026-05-05) first shipped in v11.1.0 [Q4].
- **Timers.** Under HVF, the EL1 virtual timer (`CNTV_*`) is handled by Hypervisor.framework. Physical-timer registers (`CNTP_*`) trap to QEMU and are emulated in software ("PTimer") [Q3]. The cost difference is inferred from the code, not measured.
- **Exception level.** HVF guests run at EL1 unless nested virtualisation is enabled. QEMU checks `hv_vm_config_get_el2_supported()` at runtime on macOS 15+ and fails with "Nested virtualization not supported on this system" otherwise [Q3]. Whether this M4 supports EL2 for guests was not tested (**unconfirmed**). This matters because Limine (base revision 6+) enters the kernel at EL2 with VHE if firmware hands off at EL2, and at EL1 otherwise [M2].

## 2. Debugging

### 2.1 Which debuggers run on arm64 macOS

| Debugger | Status on this host | Targets |
|---|---|---|
| Apple lldb-1700.0.9.502 (Command Line Tools) | installed; recognises and disassembles x86_64, AArch64 and riscv64 ELF files [L6] | all three, through `gdb-remote` [L6] |
| `x86_64-elf-gdb` 18.1 | installed; native arm64 Mach-O, configured `--host=aarch64-apple-darwin24.6.0 --target=x86_64-elf` [L6] | x86_64 [B2] |
| `aarch64-elf-gdb` 18.1 | not installed; `arm64_sequoia` bottle exists [B3] | AArch64 |
| `riscv64-elf-gdb` 18.1 | not installed; `arm64_sequoia` bottle exists [B4] | riscv64 |
| `gdb` 18.1 | not installed; `arm64_sequoia` bottle exists. On Apple silicon the formula builds with `--enable-targets=all` and a faked `--target=x86_64-apple-darwin20` [B1] | all targets, remote only (implied by the formula; not tested, **unconfirmed**). The caveat says native debugging needs codesigning [B1] |

### 2.2 Live gdbstub tests

Each test started QEMU halted (`-S -gdb tcp:...`) with a bare-metal test kernel. The debugger then set a software breakpoint on `kmain`, did two instruction steps, set a hardware breakpoint and a write watchpoint, read system registers, sent `monitor info registers` (`qRcmd`), and killed the guest [L6].

| | AArch64 HVF | AArch64 TCG | riscv64 TCG | x86_64 TCG |
|---|---|---|---|---|
| lldb `gdb-remote` connects | yes | yes | yes | yes |
| Software breakpoint | yes | yes | yes | yes |
| Instruction step | yes | yes | yes | yes |
| Hardware breakpoint (`breakpoint set -H`) | yes | yes | yes | yes |
| Write watchpoint | yes | not run | yes | yes |
| System registers | `SCTLR_EL1`, `TCR_EL1`, `MAIR_EL1`, `VBAR_EL1`, `ID_AA64DFR0_EL1` | `SCTLR_EL1`, `VBAR_EL1` | `sstatus`, `satp`, `stvec` | `cr3` |
| `monitor info registers` | yes (shows `EL1h`) | not run | yes (shows `priv S`) | yes |
| `x86_64-elf-gdb` (same checks) | n/a | n/a | n/a | all yes |

Notes:

- `CurrentEL` isn't exposed as an lldb register name over QEMU's AArch64 stub [L6]. `monitor info registers` shows the exception level (`PSTATE=... EL1h`).
- A 32-bit x86 test kernel failed under both debuggers: gdb reported "Remote 'g' packet reply is too long", and lldb couldn't read registers. That was because `qemu-system-x86_64` reports 64-bit registers [L6]. The 64-bit test kernel worked. Limine enters x86-64 kernels already in long mode [M2], so this only matters for 32-bit trampoline code.
- On this host, lldb alone covered every check above for all three targets [L6]. `x86_64-elf-gdb` was also tested, on x86_64 only.

## 3. Toolchain

| | x86_64 | AArch64 | riscv64 |
|---|---|---|---|
| Apple clang 17 `-print-targets` | `x86-64` listed | `aarch64` listed | **not listed** (only AArch64/ARM/X86 families) [L2] |
| Apple clang 17 compiles a freestanding ELF object (`--target=<arch>-unknown-none-elf -ffreestanding`) | yes | yes | no: "No available targets are compatible with triple" [L2] |
| Apple clang 17 driver links with `-fuse-ld=lld` | **no**: the driver uses the Darwin link path and `ld64.lld` fails with "unhandled file type" [L3] | yes, invokes `ld.lld` [L3] | n/a |
| `ld.lld` called directly | yes [L3] | yes [L3] | yes [L3] |
| Homebrew clang 23.1.4 (`/opt/homebrew/opt/llvm/bin/clang`) | driver invokes `/opt/homebrew/bin/ld.lld` [L3] | `aarch64` listed [L2] | `riscv64` listed; compiled and linked a kernel that ran in QEMU [L2][L4] |

- The `ld.lld` on `PATH` is Homebrew's `lld` 23.1.4, not part of Apple's toolchain. The Command Line Tools contain no `ld.lld`; their linkers are `ld` and `ld-classic` [L3]. LLD's docs rate AArch64, RISC-V and x86-64 ELF support "production quality" [V1].
- Homebrew `llvm` is already installed ("Installed (on request)") and is keg-only (`keg_only :provided_by_macos`), so it is used by full path [L2][B5]. The formula builds `-DLLVM_TARGETS_TO_BUILD=all`. LLD and LLDB are separate formulae [B5].
- The Limine C template compiles with `-target $(ARCH)-unknown-none-elf` and links through the compiler driver with `-fuse-ld=lld` [M3]. With Apple clang that driver link would fail for x86_64 (row above). Calling `ld.lld` directly or using Homebrew clang avoids this; applying it to the template itself is untested.
- Freestanding flags the template uses [M3]:
  - x86_64: `-march=x86-64 -mno-mmx -mno-sse -mno-red-zone -mcmodel=kernel`
  - AArch64: `-mcpu=generic -march=armv8-a+nofp+nosimd -mcmodel=small`
  - riscv64: `-mabi=lp64`

## 4. Reference material

| | x86_64 | AArch64 | riscv64 |
|---|---|---|---|
| Architecture manual | Intel SDM: free PDFs, updated 2026-10-09. Vol. 3 (System Programming), order no. 325384-093US, is 1,602 pages [S1][S2] | Arm ARM for A-profile (DDI0487): current issue, page count and access terms **unconfirmed** (Arm's site renders client-side and returned no content) [A1] | Ratified ISA manual `20250508`: Privileged 221 pages, Unprivileged 727 pages [R1]. SBI v3.0 (ratified 2025-07-16): 111 pages [R2]. PLIC 1.0.0 [R3]. AIA (latest tag `20250312`) [R4] |
| MIT xv6 | `xv6-public`: 32-bit (`-m32`, `elf_i386`). README: "we have stopped maintaining the x86 version of xv6" [X2] | no xv6 port in the `mit-pdos` organisation (it has `xv6-public`, `xv6-riscv`, books, `xv6iris`) [X4] | `xv6-riscv`: active (pushed 2026-11-05), used by MIT 6.1810 Fall 2026, with the online "xv6-riscv-book" [X1][X3] |
| Limine templates | `limine-c-template` (default `ARCH`) and `limine-c-template-x86-64` [M3][M4] | `limine-c-template` with `ARCH=aarch64` [M3] | `limine-c-template` with `ARCH=riscv64` [M3] |
| OSDev wiki | "Limine Bare Bones" targets x86-64 only (fetched from OSDev.wiki, a Miraheze-hosted site; its relationship to wiki.osdev.org is **unconfirmed**) [O1] | depth of coverage **unconfirmed** (wiki.osdev.org returned 403 or a Cloudflare challenge) [O2] | depth of coverage **unconfirmed** [O2] |
| Other tutorials seen | not surveyed | `s-matyukevich/raspberry-pi-os` and `bztsrc/raspi3-tutorial`, both aimed at Raspberry Pi hardware rather than QEMU `virt`; last pushed 2024 [X5] | not surveyed |

Notes:

- xv6-riscv is the closest teaching reference for a RISC-V kernel on QEMU `virt`. Its kernel sources come to about 151 KB in total [X1]. It differs from a Limine boot:
  - It boots with `-bios none` and runs its own M-mode `start.c` [X1]. Limine instead enters in S-mode above OpenSBI and edk2 [M2][Q9].
  - Its timer uses the Sstc `stimecmp` CSR [X1].
  - It uses Sv39 paging [X1].
  - Its Makefile expects GNU cross tools (`riscv64-unknown-elf-` and similar) [X1]. Building it with LLVM is **unconfirmed**.
- Limine's own protocol document covers all four of its architectures in one spec [M2].

## 5. Bring-up cost before one user-mode process runs

What Limine hands over comes from its "Machine State at Entry" section [M2]. The remaining work is what the kernel must still do for the First process tree: traps, a timer, a console, paging for user space, system-call entry, and return to user mode. The work items are taken from the cited manuals and from QEMU's device model. How long each takes isn't estimated here.

| | x86_64 | AArch64 | riscv64 |
|---|---|---|---|
| **Firmware below the kernel on QEMU** | SeaBIOS or OVMF; Limine supports both [M1][M3] | edk2 (UEFI) [M1][M3] | OpenSBI (M-mode; QEMU 11.1.2 ships v1.8.1, which reports SBI 3.0) runs first, then edk2 from pflash0 as S-mode firmware [L4][L5][Q9] |
| **Limine hands over** | Long mode, 4-level paging, a Limine GDT with "at least" 16/32/64-bit ring-0 code and data descriptors (no user segments guaranteed). Base revision 5+: no TSS, no IDT (IDTR base 0, limit 0), LAPIC enabled with all LVTs masked, legacy PIC and I/O APIC entries masked. Interrupts off [M2] | EL1 (or EL2+VHE, revision 6+), MMU and caches on, 4 KiB granule, `TTBR1_EL1` higher-half tables, `TTBR0_EL1` free, `VBAR_EL1` undefined. Revision 6+: `CPACR_EL1 = 0`, so FP/SIMD is off. D/A/I/F masked [M2] | S-mode, paging on (default Sv48, minimum Sv39), `stvec = 0` (revision 6+), `sie = 0` [M2] |
| **Trap and exception entry** | Build an IDT (SDM Vol. 3A §7.10) [S1] | Build a `VBAR_EL1` table of 16 entries, 0x80 apart: sync/IRQ/FIQ/SError, for each of current-EL-SP0, current-EL-SPx (+0x200), lower-EL AArch64 (+0x400) and lower-EL AArch32 (+0x600) [Q10] | Set `stvec` and decode `scause` (Privileged spec ch. 12, Supervisor-Level ISA v1.13) [R1] |
| **Kernel stack on entry from user mode** | Create and `LTR` a 64-bit TSS: "a 64-bit task state segment (TSS) must exist"; it holds `RSP0` and the IST pointers (SDM §10.7) [S1]. Also add GDT user code and data descriptors (Limine guarantees none) [M2] | Exceptions from EL0 use the lower-EL vector group (+0x400), and exceptions at EL1 with `PSTATE.SP` set use +0x200 [Q10]. The stack-pointer banking rules come from the Arm ARM (**unconfirmed** in this session) | Software swaps in a kernel pointer from `sscratch` with `CSRRW` at trap entry ("Typically, sscratch is used to hold a pointer to the hart-local supervisor context", Privileged spec §12.1.6) [R1] |
| **System-call entry** | `SYSCALL`/`SYSRET` via `IA32_STAR`, `IA32_LSTAR`, `IA32_FMASK` and `EFER.SCE` (SDM Fig. 6-14) [S1], or an `INT n` gate in the IDT | `SVC` from EL0, then `ERET` (Arm ARM; **unconfirmed** in this session) | `ecall` from U-mode, then `sret` [R1] |
| **Timer** | LAPIC timer (SDM ch. 13, APIC) [S1]. Limine has a TSC-frequency feature [M2]. Whether LAPIC-timer calibration is needed: **unconfirmed** | Generic Timer. Under HVF, `CNTV_*` is the accelerated path and `CNTP_*` is emulated in software [Q3] | SBI TIME extension (`sbi_set_timer`) [R2] or Sstc `stimecmp` (Privileged spec ch. 19) [R1]. QEMU's default CPU reports `sstc` [L4] |
| **Interrupt controller** | LAPIC and I/O APIC, found through ACPI MADT (Limine's RSDP feature) [M2][S1] | GICv2 under TCG by default, GICv3 only under HVF's vGIC (section 1.3) [Q5] | SiFive PLIC on QEMU `virt` (`aia=` "is assumed to be 'none' which selects SiFive PLIC"); AIA (APLIC/IMSIC) is opt-in [Q9][R3][R4] |
| **Serial console** | 16550 at I/O port `0x3F8` (port I/O). Used by the test kernel [L4] | PL011 at `0x09000000` (MMIO). Used by the test kernel [L4][Q8] | NS16550 at `0x10000000` (MMIO) [L4][Q9], or SBI DBCN for early output [R2] |
| **Device discovery** | ACPI [M2] | Device tree from Limine's DTB feature, or ACPI from edk2 [M2] | Device tree from Limine's DTB feature [M2] |
| **Power-off for the automated QEMU test** | `isa-debug-exit` device (exit code `(value << 1) \| 1`). Used here [L4] | PSCI `SYSTEM_OFF` through `HVC`. Used here under HVF and TCG [L4] | SiFive test device at `0x100000` [L4][Q9] or SBI SRST [R2] |

## 6. Adjacent facts (outside the ticket's bullets)

- The map says "done" includes a QEMU test in GitHub Actions. GitHub documents arm64 Linux hosted runners (`ubuntu-22.04-arm`, `ubuntu-24.04-arm`, `ubuntu-26.04-arm`) for public and private repositories [G1]. They became generally available for public repositories on 2025-08-07 [G2].
  - The runner docs say Linux runners "support hardware acceleration for Android SDK tools", but they don't mention KVM [G1]. Whether a QEMU guest gets KVM there is **unconfirmed**.
  - Without KVM, every architecture runs under TCG in CI, and an AArch64 kernel would see the TCG GIC default ([section 1.3](#13-hvf-limitations-that-matter-for-kernel-work-aarch64-only)).
- The tool list in the map's Host note is slightly out of date. This host also has:
  - Homebrew `llvm` 23.1.4, with a RISC-V backend [L2]
  - `x86_64-elf-gdb` 18.1 [L6]
  - Homebrew `gcc-16`, a native compiler (`-dumpmachine` prints `aarch64-apple-darwin24`), not a cross-compiler [L2]

## 7. Unconfirmed items

- The Arm ARM (DDI0487): current issue, page count and access terms. AArch64 details attributed to it above (stack-pointer banking, `SVC`/`ERET`) weren't re-read in this session.
- The OSDev wiki's depth of coverage for each architecture. wiki.osdev.org blocked automated fetches. Only the OSDev.wiki "Limine Bare Bones" page was read.
- Limine's own boot time on each target, and a full Limine boot of the template on this host.
- Homebrew `gdb` (`--enable-targets=all`) driving AArch64 and riscv64 QEMU stubs on arm64 macOS (implied by the formula, not tested).
- Whether this M4 supports nested virtualisation (EL2) under HVF.
- KVM availability on GitHub-hosted runners.
- Building xv6-riscv with LLVM instead of GNU cross tools.
- Whether the LAPIC timer needs calibration under QEMU.

## Appendix A: How the local measurements were made

All files lived in the session scratchpad. Nothing was installed and no system settings changed. `cp` copied UEFI variable-store templates into the scratchpad, so Homebrew's files were never written.

- **L1, accelerators:** `qemu-system-{aarch64,x86_64,riscv64} -accel help`
- **L2, compilers:**
  - `clang -print-targets` and `/opt/homebrew/opt/llvm/bin/clang -print-targets`
  - `clang --target=<arch>-unknown-none-elf -ffreestanding -nostdlib -c k.c` for each target
  - `brew info llvm`
- **L3, linkers:**
  - `ld.lld --version` (reports "Homebrew LLD 23.1.4")
  - `ld.lld -static -T link.ld` on each object
  - `clang --target=x86_64-unknown-none-elf -fuse-ld=lld ...`, with and without `-###`
  - a listing of `/Library/Developer/CommandLineTools/usr/bin`
- **L4, bare-metal test kernels.** Each prints `nova:start`, runs `for (i = 0; i < N; i++) sink += i` on a `volatile` 64-bit variable, prints `nova:done`, then powers off. Writable data was page-aligned for the reported numbers. Timing is wall clock from QEMU launch to QEMU exit, with `-m 256M -display none -serial stdio`.
  - AArch64: `-M virt -kernel` an ELF at `0x40080000`. PL011 for output, PSCI `SYSTEM_OFF` via `hvc #0`. Run with `-cpu host -accel hvf` and with `-cpu max -accel tcg`.
  - riscv64: `-M virt -bios default -kernel` an ELF at `0x80200000`, built with Homebrew clang (`-march=rv64imac -mabi=lp64 -mcmodel=medany`). NS16550 for output, SiFive test device to power off.
  - x86_64: `-M pc -kernel` a flat binary with a Multiboot 1 header using the a.out-kludge address fields. A 32-bit entry stub enables PAE, `EFER.LME` and paging, then jumps to 64-bit C. COM1 for output, `-device isa-debug-exit,iobase=0xf4`.
- **L5, firmware:** time from QEMU launch until "UEFI Interactive Shell" appears on serial, with `-nic none`, edk2 from `/opt/homebrew/share/qemu` in pflash unit 0 (read-only), and a scratch vars copy in unit 1. Run with and without `-boot menu=on,splash-time=0`. The serial log showed `UEFI firmware (version edk2-stable202408-prebuilt.qemu.org ...)`.
- **L6, debuggers:** QEMU with `-S -gdb tcp:127.0.0.1:<port>`.
  - `lldb --batch -o "target create <elf>" -o "gdb-remote 127.0.0.1:<port>"`, then `breakpoint set -n kmain`, `thread step-inst`, `breakpoint set -H -a ...`, `watchpoint set variable -w write sink`, `register read <sysreg>`, `process plugin packet monitor info registers`, `process kill`.
  - The same sequence with `x86_64-elf-gdb -batch`: `target remote`, `break`, `stepi`, `hbreak`, `watch`, `info registers cr3`, `monitor info registers`.
  - Also ran `x86_64-elf-gdb -batch -ex "show configuration"` and `file` on the gdb binary.

## Sources

QEMU (at tag `v11.1.2`, the installed version):

- **[Q1]** `meson.build` L304–L318, `accelerator_targets`: https://github.com/qemu/qemu/blob/v11.1.2/meson.build#L304-L318
- **[Q2]** QEMU docs, "Introduction", virtualisation accelerators table: https://www.qemu.org/docs/master/system/introduction.html
- **[Q3]** `target/arm/hvf/hvf.c`: https://github.com/qemu/qemu/blob/v11.1.2/target/arm/hvf/hvf.c
  - L124–L158: hardware breakpoint and watchpoint counts from `ID_AA64DFR0_EL1`
  - L1311–L1371: EL2 check and vGIC creation on macOS 15
  - L1736–L1742 and L2047–L2052: PTimer emulation
  - L2231–L2327: vtimer
  - L2347–L2389: debug exception handling
  - L2559–L2562 and L2614: stepping
  - L2716–L2915: breakpoint insertion and `hvf_arch_update_guest_debug`
- **[Q4]** Commit history of `target/arm/hvf/hvf.c`: https://github.com/qemu/qemu/commits/master/target/arm/hvf/hvf.c
  - `eb2edc42b126` (2023-06-06) is in `v8.1.0` but not `v8.0.0`, per GitHub compare `eb2edc42b126...v8.0.0` (behind) and `...v8.1.0` (ahead).
  - `d7a75ea483a5` (2026-05-05) is in `v11.1.0` but not `v11.0.0`.
- **[Q5]** `hw/arm/virt.c`: https://github.com/qemu/qemu/blob/v11.1.2/hw/arm/virt.c
  - L2624–L2638: default GIC selection
  - L2717–L2724: GIC versions supported under HVF
  - L2799–L2800: ITS refusal
  - L4111–L4118: `get_kernel_irqchip_default`
  - L4449–L4456: `virt-11.0` sets `hvf_no_kernel_irqchip_default`
- **[Q6]** `accel/hvf/hvf-all.c` L233–L284, the `kernel-irqchip` property: https://github.com/qemu/qemu/blob/v11.1.2/accel/hvf/hvf-all.c#L233-L284
- **[Q7]** `docs/system/gdb.rst`, "Breakpoint and Watchpoint support" and "Changing single-stepping behaviour": https://github.com/qemu/qemu/blob/v11.1.2/docs/system/gdb.rst
- **[Q8]** `docs/system/arm/virt.rst` (CPU types, `gic-version`, PL011): https://github.com/qemu/qemu/blob/v11.1.2/docs/system/arm/virt.rst
- **[Q9]** `docs/system/riscv/virt.rst` (devices including PLIC, NS16550, SiFive Test; the `aia=` option; pflash boot of edk2): https://github.com/qemu/qemu/blob/v11.1.2/docs/system/riscv/virt.rst
- **[Q10]** `target/arm/helper.c` L9390–L9490, AArch64 exception vector offsets: https://github.com/qemu/qemu/blob/v11.1.2/target/arm/helper.c#L9390-L9490

Homebrew:

- **[B1]** `gdb`: https://formulae.brew.sh/formula/gdb and https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/g/gdb.rb
- **[B2]** `x86_64-elf-gdb`: https://formulae.brew.sh/formula/x86_64-elf-gdb and https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/x/x86_64-elf-gdb.rb
- **[B3]** `aarch64-elf-gdb`: https://formulae.brew.sh/formula/aarch64-elf-gdb and https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/a/aarch64-elf-gdb.rb
- **[B4]** `riscv64-elf-gdb`: https://formulae.brew.sh/formula/riscv64-elf-gdb and https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/r/riscv64-elf-gdb.rb
- **[B5]** `llvm`: https://formulae.brew.sh/formula/llvm and https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/l/llvm.rb

Bottle availability for B1–B5 was also read locally with `brew info --json=v2`, which reported an `arm64_sequoia` bottle for each.

LLVM:

- **[V1]** LLD home page (supported ELF targets and maturity): https://lld.llvm.org/

Limine:

- **[M1]** Limine README (v12.x), "Supported architectures" and "Minimum system requirements": https://github.com/limine-bootloader/limine/blob/v12.x/README.md
- **[M2]** Limine boot protocol, `PROTOCOL.md`: https://github.com/limine-bootloader/limine-protocol/blob/HEAD/PROTOCOL.md
  - "Machine State at Entry" (x86-64, aarch64, riscv64)
  - "Paging Mode Feature"
  - "Device Tree Blob Feature", "RSDP Feature", "TSC Frequency Feature"
  - "Firmware Type Feature"
- **[M3]** `limine-c-template`: https://github.com/limine-bootloader/limine-c-template, including `README.md`, `GNUmakefile` (QEMU flags, `run-bios`) and `kernel/GNUmakefile` (per-architecture flags)
- **[M4]** Limine-Bootloader organisation repositories (`limine-c-template-x86-64`): https://github.com/limine-bootloader
- **[M5]** Limine `CONFIG.md`, the `timeout` option: https://github.com/limine-bootloader/limine/blob/v12.x/CONFIG.md

Architecture manuals:

- **[S1]** Intel SDM Vol. 3 (3A–3D), order no. 325384-093US, 1,602 pages: https://cdrdv2.intel.com/v1/dl/getContent/671447
  - §7.10 Interrupt Descriptor Table
  - §10.7 Task Management in 64-bit Mode
  - Fig. 6-14 "MSRs Used by SYSCALL and SYSRET"
  - Ch. 13 APIC
- **[S2]** Intel SDM landing page ("Updated 10/9/2026"): https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- **[A1]** Arm ARM for A-profile, DDI0487: https://developer.arm.com/documentation/ddi0487/latest/ (content could not be retrieved; see section 7)
- **[R1]** RISC-V ISA Manual, release `20250508`: https://github.com/riscv/riscv-isa-manual/releases/tag/20250508
  - `riscv-privileged-20250508.pdf`, 221 pages: ch. 12 Supervisor-Level ISA v1.13 (§12.1.6 `sscratch`); ch. 19 Sstc
  - `riscv-unprivileged-20250508.pdf`, 727 pages
- **[R2]** RISC-V SBI Specification v3.0, ratified 2025-07-16, 111 pages: https://github.com/riscv-non-isa/riscv-sbi-doc/releases/tag/v3.0
  - ch. 5 Legacy, ch. 6 TIME, ch. 10 SRST, ch. 12 DBCN
- **[R3]** RISC-V PLIC Specification 1.0.0 (2023-03-12): https://github.com/riscv/riscv-plic-spec/releases
- **[R4]** RISC-V AIA Specification (releases `1.0`, `20250312`): https://github.com/riscv/riscv-aia/releases

Teaching kernels:

- **[X1]** `mit-pdos/xv6-riscv`: https://github.com/mit-pdos/xv6-riscv
  - `README`
  - `Makefile` (TOOLPREFIX detection, `QEMUOPTS = -machine virt -bios none ...`)
  - `kernel/start.c` (M-mode setup, `stimecmp`)
  - `kernel/riscv.h` (`SATP_SV39`)
- **[X2]** `mit-pdos/xv6-public`: https://github.com/mit-pdos/xv6-public, including `README` and `Makefile` (`-m32`, `elf_i386`)
- **[X3]** MIT 6.1810 (Fall 2026), linking the xv6 book: https://pdos.csail.mit.edu/6.1810/ and https://mit-pdos.github.io/xv6-riscv-book/
- **[X4]** `mit-pdos` repositories matching "xv6": https://github.com/orgs/mit-pdos/repositories?q=xv6
- **[X5]** AArch64 tutorials: https://github.com/s-matyukevich/raspberry-pi-os and https://github.com/bztsrc/raspi3-tutorial

OSDev:

- **[O1]** OSDev.wiki, "Limine Bare Bones": https://osdev.wiki/wiki/Limine_Bare_Bones
- **[O2]** wiki.osdev.org (HTTP 403 and Cloudflare challenge on fetch): https://wiki.osdev.org/

GitHub Actions:

- **[G1]** GitHub-hosted runners reference: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- **[G2]** GitHub changelog, "arm64 hosted runners for public repositories are now generally available" (2025-08-07): https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/

Local checks on this host:

- **[L1]–[L6]**: see [Appendix A](#appendix-a-how-the-local-measurements-were-made).
