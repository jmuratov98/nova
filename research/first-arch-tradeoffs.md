# First-architecture bring-up trade-offs: x86-64, AArch64, RISC-V 64

Research for [issue #3](https://github.com/jmuratov98/nova/issues/3), a child of the roadmap map [#1](https://github.com/jmuratov98/nova/issues/1). It feeds the first-architecture grilling ticket ([#4](https://github.com/jmuratov98/nova/issues/4)).

**Question.** What does bringing up each of x86-64, AArch64 and RISC-V 64 as Nova's *first* architecture cost? The developer works solo, writes a C23 kernel to learn, and uses an Apple M4 host with QEMU.

**Scope.** This file gives facts and trade-offs only. It does **not** recommend an architecture, because that choice belongs to the first-architecture ticket. All three architectures are Version 1 targets either way, so the question is about order, not inclusion.

**Method.** Claims are cited to primary sources: architecture manuals and specs, QEMU docs and source, the Limine protocol, Apple Hypervisor docs, Linux boot docs, and xv6-riscv. Items marked **[host]** were checked on the dev host:

- Apple M4, macOS 15.6 (24G84)
- Homebrew QEMU 11.1.2
- Apple clang 17.0.0, Homebrew LLVM/clang 23.1.4, Homebrew LLD 23.1.4
- Apple lldb-1700

The OSDev wiki is a secondary source. It returned HTTP 403 to automated fetches, so this file uses it only as a pointer.

---

## 1. Headline comparison

| Dimension | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| **QEMU on the M4 host** | `qemu-system-x86_64`, **TCG only** (emulation) [host] | `qemu-system-aarch64`, **HVF** (hardware virtualization) or TCG [host] | `qemu-system-riscv64`, **TCG only** [host] |
| **Machine model** | `q35` (PCIe, ACPI) or `microvm` (virtio-mmio) | `virt` (devicetree, virtio-mmio ×32, PCIe, PL011, GICv2/3/4) | `virt` (devicetree, virtio-mmio ×8, PCIe, 16550, CLINT/ACLINT + PLIC or AIA) |
| **Shortest boot path** | Limine (BIOS or UEFI) puts you in long mode with paging on. QEMU `-kernel` only takes 32-bit Multiboot 1 or PVH, so you write the 32→64-bit trampoline yourself | QEMU `-kernel` ELF jumps straight to EL1 (MMU off, DTB at start of RAM). Limine via UEFI is also an option | QEMU `-kernel` with the built-in OpenSBI enters S-mode with `a0`=hartid, `a1`=DTB. `-bios none` gives M-mode, as xv6 does. Limine via UEFI is also an option |
| **Legacy baggage before "hello"** | High: GDT, TSS, IDT, segment state, 8259 PIC masking, the long-mode switch if not using Limine | Low: exception vector table plus system registers | Lowest: `stvec`, a few CSRs |
| **Paging** | 4-level (48-bit) or 5-level (LA57), single CR3, kernel half shared by convention | VMSAv8-64: split TTBR0/TTBR1, 4K/16K/64K granules, MAIR attributes, explicit TLB/barrier discipline | Sv39/Sv48/Sv57: single `satp`, the simplest PTE format, `sfence.vma` |
| **Interrupts / timer** | LAPIC + IOAPIC (+ legacy PIC to mask), MSI. Timer: LAPIC/TSC-deadline, needs frequency calibration or CPUID | GICv3 (system-register CPU interface) + Arm generic timer with frequency in `CNTFRQ_EL0` | PLIC (or AIA APLIC/IMSIC). Timer via SBI TIME or `stimecmp` (Sstc), frequency from DT |
| **Syscall entry** | `SYSCALL`/`SYSRET` (MSRs, manual stack switch, `SWAPGS`) | `SVC` → `VBAR_EL1` vector, banked `SP_EL1` | `ecall` → `stvec`, `sscratch` swap |
| **Device discovery on QEMU** | ACPI (RSDP→MADT/MCFG/…); a full ACPI stack needs AML | Devicetree by default; ACPI via UEFI | Devicetree by default; ACPI available with UEFI |
| **SMP bring-up** | INIT-SIPI-SIPI with a real-mode trampoline, or Limine MP | PSCI `CPU_ON` (HVC conduit on QEMU virt) or Limine MP | SBI HSM `hart_start` or Limine MP |
| **Debugger on host** | QEMU gdbstub + lldb works [host]. Homebrew `gdb` (all targets) | gdbstub works under **both TCG and HVF** (single-step verified under HVF) [host] | gdbstub + lldb works [host] |
| **Toolchain on host** | Apple clang targets it [host] | Apple clang targets it [host] | **Apple clang has no RISC-V backend**. Homebrew LLVM 23 does [host] |
| **Canonical teaching kernel** | xv6 (x86, 32-bit, **no longer maintained**) | No xv6. Tutorials mostly target Raspberry Pi | **xv6-riscv** (maintained, MIT 6.1810, runs on QEMU `virt`) |
| **Manual size / reading cost** | Intel SDM: four volumes, several thousand pages | Arm ARM (DDI 0487): the largest of the three, plus separate GIC and PSCI specs | Privileged spec is a single comparatively short volume, plus the SBI spec |

---

## 2. QEMU support and acceleration on the M4 host

### 2.1 What the host can do (verified)

`qemu-system-<arch> -accel help` on QEMU 11.1.2 [host]:

| Binary | Accelerators |
|---|---|
| qemu-system-x86_64 | `tcg` |
| qemu-system-aarch64 | `hvf`, `tcg` |
| qemu-system-riscv64 | `tcg` |

QEMU's docs list HVF as available on macOS hosts for x86 and Arm *host* architectures. TCG is "a JIT … capable of emulating many CPUs" and is "purely emulated" ([QEMU intro](https://www.qemu.org/docs/master/system/introduction.html)). HVF runs the guest only on the host's own ISA, so on an M4 only AArch64 guests are hardware-accelerated.

### 2.2 Rough speed (host micro-benchmark)

I ran one tiny bare-metal kernel per architecture. Each ran a 4-instruction register-only ALU loop 10⁹ times and then wrote a byte to the UART. I timed it to the UART byte, subtracted the cost of a 1-iteration run, and took the best of 3 runs [host]:

| Configuration | 10⁹ loop iterations |
|---|---|
| aarch64 `virt`, **HVF**, `-cpu host` | **0.45 s** (≈ native: ~2 cycles/iter at M4 clocks) |
| riscv64 `virt`, TCG | 0.62 s |
| aarch64 `virt`, TCG, `-cpu max` | 1.02 s |
| x86_64 `q35`, TCG (32-bit Multiboot code) | 1.45 s |

Caveat: a register-only loop is TCG's **best case**, because translated blocks chain together and there are no guest memory accesses. Under TCG, every guest load and store also goes through QEMU's software MMU/TLB. Every MMIO access, interrupt or timer event costs exits or emulation in all modes. Real kernel workloads (page-table walks, context switches, virtio I/O) will widen the gap between HVF and TCG beyond the roughly 2–3× shown here. For a learning kernel's boot-and-test loop, all four configurations are interactive-speed.

A second probe timed edk2 firmware to the UEFI shell [host]:

| Configuration | Time to shell |
|---|---|
| x86_64 TCG | 1.1 s |
| riscv64 TCG | 0.8 s |
| aarch64 HVF | 5.2 s |
| aarch64 TCG | 5.5 s |

The aarch64 edk2 time is dominated by firmware delays, not CPU speed. Firmware boot is therefore not a useful acceleration signal.

### 2.3 HVF-specific constraints for an AArch64 guest (verified)

These were observed with QEMU 11.1.2 on the M4 [host]:

- **The guest enters at EL1.** A probe kernel read `CurrentEL` = `0x4` (EL1) under HVF. TCG with `-M virt,virtualization=on` gave `0x8` (EL2).
- **GIC.** `gic-version=2` fails with "HVF does not support GICv2 emulation". GICv3 works and uses Apple's hardware vGIC. `its=on` fails with "ITS not supported on HVF when using the hardware vGIC", so MSIs use GICv2m. The generated DTB contains `arm,gic-v3` and an `arm,gic-v2m-frame`.
- **No TrustZone.** `secure=on` fails with "HVF does not support providing Security extensions (TrustZone)".
- **Nested EL2 is not usable today.** `virtualization=on` is accepted, but QEMU aborts with `HV_BAD_ARGUMENT` at `target/arm/hvf/hvf.c:1076` when it boots a kernel. Hypervisor.framework has EL2 APIs ([Apple: Apple Silicon / Nested virtualization](https://developer.apple.com/documentation/hypervisor/apple-silicon)), and the QEMU HVF nested-virt/vGIC series is in review ([patchew v15 cover](https://patchew.org/QEMU/20260306130107.35359-1-mohamed@unpredictable.fr)). A reviewer on that series notes that macOS supports nested virt only on M3 and later. One developer reported that EL2 did not take effect ([Apple forum](https://developer.apple.com/forums/thread/775546)). **Implication:** under HVF, Nova runs at EL1. The EL2/VHE entry described by Limine base revision 6 and recommended by Linux would only be exercised under TCG.
- **Page granules.** Under HVF, `ID_AA64MMFR0_EL1` = `0x000010000f100022`. That decodes to:
  - TGran4 supported
  - TGran16 supported
  - **TGran64 not supported**
  - PARange = 40-bit PA
  - 16-bit ASIDs

  TCG `-cpu max` reports all granules and 52-bit PA (`0x2100032310201126`). **A kernel that assumes a 64 KiB granule will not run under HVF.**
- **PSCI.** The conduit is `hvc` (DTB `psci { method = "hvc"; compatible = "arm,psci-1.0" … }`).
- **Timer.** The generic timer appears as `arm,armv8-timer` with PPIs 13/14/11/10 (DT numbering), which are the secure-phys, non-secure-phys, virt and hyp-phys timers.

### 2.4 Machine models per architecture

**AArch64 `virt`** ([QEMU arm/virt](https://www.qemu.org/docs/master/system/arm/virt.html)):

- PCIe, 32 virtio-mmio transports by default, one or two PL011 UARTs.
- GICv2 (≤ 8 CPUs), GICv3 (≤ 512), GICv4 (needs `virtualization=on`), and an experimental GICv5.
- The `acpi=on|off|auto` option.
- The `host` CPU only with KVM/HVF.

**RISC-V `virt`** ([QEMU riscv/virt](https://www.qemu.org/docs/master/system/riscv/virt.html)):

- CLINT, PLIC, one or two NS16550 UARTs, 8 virtio-mmio transports, one PCIe host bridge.
- `aclint=on` (TCG only).
- `aia=none|aplic|aplic-imsic`.
- `acpi=on` by default, with tables exposed through fw_cfg.
- Default firmware is OpenSBI.

The default rv64 CPU advertises these extensions in the DTB [host]:

- `mmu-type = "riscv,sv57"`, so Sv39/48/57 are all available.
- `sstc`, `svadu`, `zicbom`/`zicboz`, `h`.

The OpenSBI v1.8.1 banner reports standard SBI extensions `time, rfnc, ipi, base, hsm, srst, pmu, dbcn, fwft, legacy, dbtr, sse`. It uses an `aclint-mtimer @ 10000000Hz` [host].

**x86-64 `q35` / `microvm`**:

- `q35` is a PCIe/ICH9 PC whose virtio devices are PCI only. Examples include `virtio-blk-pci` and `virtio-net-pci`; the `virtio-*-device` mmio variants need a virtio-mmio bus [host].
- `microvm` is "a minimalist machine type" with up to eight virtio-mmio devices and optional i8259/i8254/RTC. It boots a host-side `-kernel` ([QEMU microvm](https://www.qemu.org/docs/master/system/i386/microvm.html)). QEMU 11.1.2 also exposes `acpi=` and `pcie=` options on microvm [host].
- `isa-debug-exit` is available for test harness exits [host].

---

## 3. Boot path and firmware / boot protocol options

Firmware images bundled with Homebrew QEMU (`/opt/homebrew/share/qemu`) [host]:

- edk2 UEFI for x86_64, aarch64 and riscv
- SeaBIOS (`bios-256k.bin`)
- OpenSBI (`opensbi-riscv64-generic-fw_dynamic.bin`)

Limine is also in Homebrew (`limine` 12.10.0) [host].

### x86-64

- **QEMU `-kernel`** accepts the Linux bzImage, **Multiboot 1** and **PVH** (ELF note `XEN_ELFNOTE_PHYS32_ENTRY`) formats ([qemu `hw/i386/x86-common.c`](https://github.com/qemu/qemu/blob/master/hw/i386/x86-common.c)). Multiboot and PVH both enter in 32-bit protected mode. An ELF64 Multiboot image is rejected with "Cannot load x86-64 image, give a 32bit one." [host]. Using `-kernel` therefore means Nova writes the 32-bit entry stub itself. That stub builds page tables, sets EFER.LME, enables paging and far-jumps to 64-bit code.
- **Legacy BIOS (SeaBIOS)** with a boot sector starts in 16-bit real mode, which means real → protected → long mode. gdb/lldb handle real mode poorly. When attached at reset, lldb shows `pc = 0xfff0` and disassembles garbage, because it ignores the CS base [host]. The QEMU gdb docs suggest `set architecture i8086` ([QEMU gdb](https://www.qemu.org/docs/master/system/gdb.html)).
- **UEFI (edk2/OVMF)** starts in 64-bit long mode with an identity map. Nova would need to be a PE/COFF UEFI application or use a loader.
- **Limine** supports x86-64 on BIOS and UEFI ([Limine README](https://github.com/Limine-Bootloader/Limine)). It also loads Multiboot 1/2 and Linux kernels. At entry ([Limine protocol, "Machine State at Entry"](https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md)):
  - The CPU is in 64-bit long mode with paging, PAE, WP and NX on, and 5-level paging if requested.
  - A bootloader GDT is loaded. The IDT is undefined ("Executable must load its own"). From base revision 5 on, no TSS is present.
  - The legacy PICs are masked. IOAPIC entries are masked, and from base revision 5 the LAPIC is put in a defined state.
  - Boot services have exited and there is a stack of at least 64 KiB.

  Even with Limine, Nova still owns its GDT, TSS and IDT.

### AArch64

- **QEMU `-kernel`**: for a Linux `Image`, the DTB address goes in `x0`. For bare-metal ELF images, "the DTB sits at the start of RAM, at 0x4000_0000" ([QEMU arm/virt](https://www.qemu.org/docs/master/system/arm/virt.html)). Default entry is EL1 with the MMU off [host].
- **Linux arm64 boot protocol** (a reference for Image-format kernels): `x0` = DTB physical address, the MMU must be off, entry is at EL2 ("RECOMMENDED") or EL1, all interrupts are masked in DAIF, and there is a 64-byte Image header with magic `0x644d5241` ([Linux arm64 booting](https://docs.kernel.org/arch/arm64/booting.html)).
- **UEFI (edk2)** and **Limine** (aarch64 is UEFI only per the [Limine README](https://github.com/Limine-Bootloader/Limine)). At Limine entry ([protocol](https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md)):
  - The MMU and caches are on, with a 4 KiB granule for TTBR0/TTBR1.
  - `TTBR1_EL1` holds the higher-half tables and `TTBR0_EL1` is free for the kernel.
  - `VBAR_EL1` is undefined, DAIF is masked, and `CPACR_EL1` = 0, so FP/SIMD traps.
  - From base revision 6, entry is at EL2 with VHE if the firmware was at EL2. Under HVF that will be EL1 (see §2.3).
- There is no legacy BIOS and no 16/32-bit mode to transit.

### RISC-V 64

- **QEMU `-kernel` with the default OpenSBI** (fw_dynamic) runs firmware in M-mode and then jumps to the kernel in **S-mode** [host: banner "Domain0 Next Mode : S-mode"]. Linux's RISC-V boot convention is `a0` = hartid, `a1` = DTB and `satp = 0` ([Linux riscv boot](https://docs.kernel.org/arch/riscv/boot.html)).
- **Pitfall [host + source].** For ELF kernels, QEMU passes OpenSBI the ELF's **lowest load address, not `e_entry`**. This is deliberate: "Use low address not ELF entry point …" ([qemu `hw/riscv/boot.c`](https://github.com/qemu/qemu/blob/master/hw/riscv/boot.c)). With LLD's default layout, a read-only header segment at `0x10000` became the jump target and the kernel never ran. A linker script that puts `_start` at the lowest address (for example `0x80200000`) fixes it [host].
- **`-bios none`** starts the kernel in **M-mode** at `0x80000000`. This is how xv6-riscv boots (`QEMUOPTS = -machine virt -bios none -kernel …`). Its `start.c` then does several things:
  - delegates traps (`medeleg`/`mideleg`) and sets up PMP
  - enables Sstc and hardware A/D updates via `menvcfg`
  - `mret`s to S-mode

  ([xv6-riscv Makefile](https://github.com/mit-pdos/xv6-riscv/blob/riscv/Makefile), [kernel/start.c](https://github.com/mit-pdos/xv6-riscv/blob/riscv/kernel/start.c)).
- **UEFI (edk2-riscv in pflash)**, **U-Boot**, and **Limine** (riscv64 is UEFI only). At Limine entry the kernel is in S-mode with `satp` set to the requested Sv39/48/57 mode, `stvec` = 0 (base revision 6+), `sie` = 0, a stack of at least 64 KiB, and boot services exited ([protocol](https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md)).
- **SBI** is the S-mode↔M-mode firmware interface. It provides timer, IPI, remote fence, HSM (hart start/stop), system reset and a debug console (DBCN) ([SBI spec](https://github.com/riscv-non-isa/riscv-sbi-doc)). A first `printf` can be an `ecall` to DBCN or legacy putchar, with no UART driver needed.

**Cross-arch note.** Limine is the one boot protocol covering all three architectures with the same request/response interface (HHDM, memory map, MP, RSDP/DTB, paging mode). It hides the most legacy setup on x86-64 and the least on RISC-V, where OpenSBI + `-kernel` is already short.

---

## 4. MMU and paging model

| | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| Formats | 4-level (48-bit VA), 5-level/LA57 (57-bit) | VMSAv8-64; 4K/16K/64K granule; 48-bit VA (52 with LPA2/LVA) | Sv39 (3-level, 512 GiB), Sv48, Sv57 |
| Roots | One `CR3` per address space. The kernel upper half is mapped into every PML4 by convention | **Two roots**: `TTBR0_EL1` (low/user) and `TTBR1_EL1` (high/kernel), sized by `TCR_EL1.T0SZ/T1SZ` | One `satp` (MODE, ASID, PPN). Same shared-upper-half convention as x86 |
| Memory types | PAT/MTRR (PCD/PWT/PAT bits) | `MAIR_EL1` indirection (Normal vs Device-nGnRE …), shareability bits | PMAs fixed by the platform. Svpbmt is optional |
| TLB / ordering | Mostly implicit. `invlpg`, CR3 reload, PCID | Explicit: `TLBI` + `DSB` + `ISB`, and the break-before-make rule when changing live mappings | `sfence.vma` (+ ASID). Software or hardware (Svadu) A/D bit updates |
| Large pages | 2 MiB, 1 GiB | Block descriptors (2 MiB/1 GiB at 4K granule), contiguous hint | Megapages/gigapages at any level |
| Gotchas | Canonical-address rule. NX needs `EFER.NXE`. SMEP/SMAP | Must program MAIR/TCR/SCTLR correctly before the MMU works at all. With the MMU off, data accesses are Device memory (slow under HVF). No 64K granule under HVF (§2.3) | A/D bits: if hardware does not set them, every first access faults. xv6 enables `menvcfg.ADUE` (Svadu); QEMU's default CPU has `svadu` [host] |

Sources:

- Intel SDM Vol. 3A ch. 4 "Paging" ([Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html))
- Arm ARM part D "The AArch64 System Level Memory Model / VMSAv8-64" ([Arm ARM DDI 0487](https://developer.arm.com/documentation/ddi0487/latest)), with the tutorial [Learn the architecture: AArch64 memory management](https://developer.arm.com/documentation/101811/latest)
- RISC-V Privileged spec "Supervisor-Level ISA" (Sv39/48/57, `satp`, `sfence.vma`) ([riscv-isa-manual releases](https://github.com/riscv/riscv-isa-manual/releases))

---

## 5. Interrupt controller and timer

**x86-64**

- **Controllers.** Each CPU has a Local APIC, used in xAPIC MMIO or x2APIC MSR mode. IOAPICs route external interrupts. The legacy 8259 PICs must be masked or remapped. PCI devices use MSI/MSI-X.
- **Timers.** The PIT, HPET and RTC are on q35. The LAPIC timer must be calibrated against a known clock, or its frequency read from CPUID leaf 0x15/0x16 where present. The TSC and TSC-deadline mode are also available; QEMU knows the `tsc-deadline` and `x2apic` CPU flags [host].
- **Sources.** Intel SDM Vol. 3A ch. 10–11 "APIC". Limine masks the PICs and IOAPIC entries for you ([protocol](https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md)).

**AArch64**

- **Controller.** The GIC has a Distributor (SPIs), per-CPU Redistributors (SGIs/PPIs, LPIs), a CPU interface through `ICC_*_EL1` system registers in GICv3, and an optional ITS for MSIs ([GICv3/v4 spec IHI 0069](https://developer.arm.com/documentation/ihi0069/latest), [Learn the architecture: GIC](https://developer.arm.com/documentation/198123/latest)). Under HVF it must be GICv3 with no ITS (§2.3).
- **Timer.** The Arm Generic Timer is per-CPU (EL1 physical/virtual), its frequency is architecturally readable in `CNTFRQ_EL0`, and it is delivered as a PPI. No calibration is needed ([Learn the architecture: Generic Timer](https://developer.arm.com/documentation/102379/latest)).

**RISC-V 64**

- **External interrupts** come from the PLIC on QEMU's default `virt`, or from AIA with `aia=aplic` / `aplic-imsic` for MSIs ([QEMU riscv/virt](https://www.qemu.org/docs/master/system/riscv/virt.html)).
- **Timer and IPIs.** The CLINT/ACLINT provides `mtime`/`mtimecmp` and software IPIs, but these are **M-mode** resources. An S-mode kernel gets timers either through the SBI TIME extension (`sbi_set_timer`) or directly through **Sstc** (`stimecmp`). It gets IPIs through the SBI IPI extension, or through IMSIC under AIA ([SBI spec](https://github.com/riscv-non-isa/riscv-sbi-doc), Privileged spec). The timebase frequency comes from the DT (`timebase-frequency`); OpenSBI reports 10 MHz [host].
- **xv6-riscv** enables Sstc and uses `stimecmp` ([start.c](https://github.com/mit-pdos/xv6-riscv/blob/riscv/kernel/start.c)).

---

## 6. Privilege levels and syscall entry

| | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| Levels | Rings 0–3 (Nova uses 0 and 3), plus SMM and VMX root/non-root | EL0 (user), EL1 (kernel), EL2 (hypervisor), EL3 (secure monitor) | U, S, M (+ HS/VS/VU with H) |
| Trap table | IDT (256 gates). Hardware pushes a frame. TSS.RSP0 gives the kernel stack on ring change, and IST gives known-good stacks for NMI/#DF/#MC | `VBAR_EL1`: 16 vectors × 128 B (current EL with SP0/SPx, lower EL AArch64/AArch32 × Sync/IRQ/FIQ/SError). Cause in `ESR_EL1`, PC in `ELR_EL1`, state in `SPSR_EL1` | `stvec` (direct or vectored). Cause in `scause`, PC in `sepc`, fault address in `stval`, state in `sstatus` |
| Syscall instruction | `SYSCALL`/`SYSRET`, configured via `STAR`/`LSTAR`/`SFMASK` MSRs. **`SYSCALL` does not switch RSP**, so the kernel uses `SWAPGS` + per-CPU data to find its stack. `SYSRET` with a non-canonical RCX is a classic security pitfall | `SVC #imm` → synchronous exception to EL1. `SP_EL1` is banked, so the stack switch is automatic. `ERET` returns | `ecall` → trap to S. Swap the stack via `sscratch` by hand. `sret` returns |
| Thread pointer (for Nova libc TLS) | `FS` base (MSR or `WRFSBASE`) | `TPIDR_EL0` | `tp` register |
| psABI references | [System V x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI) | [AAPCS64 (ARM-software/abi-aa)](https://github.com/ARM-software/abi-aa) | [RISC-V ELF psABI](https://github.com/riscv-non-isa/riscv-elf-psabi-doc) |

Sources:

- Intel SDM Vol. 2 (`SYSCALL`, `SYSRET`, `SWAPGS`) and Vol. 3A ch. 5–6 (protection, interrupts)
- Arm ARM D1 "The AArch64 Application/System Level Programmers' Model", with [Learn the architecture: AArch64 Exception Model](https://developer.arm.com/documentation/102412/latest)
- RISC-V Privileged spec, "Supervisor CSRs"

Relevance to the **Syscall ABI**: the register convention for syscall number and arguments differs on every architecture, so each one gets its own arch-specific Syscall ABI binding. Linux's per-arch conventions are a reference point, not an authority.

---

## 7. Device discovery: ACPI vs devicetree

- **x86-64 on q35: ACPI.**
  - The RSDP is found via Limine/UEFI or a BIOS memory scan. It leads to the XSDT, then MADT (CPUs, APICs, IRQ overrides), MCFG (PCIe ECAM), HPET and FADT.
  - The static tables can be parsed by hand.
  - Anything in **AML** needs an interpreter, such as [ACPICA](https://www.intel.com/content/www/us/en/developer/topic-technology/open/acpica/overview.html) or [uACPI](https://github.com/uACPI/uACPI). That includes the S5 power-off method, `_PRT` PCI interrupt routing, and device `_CRS`.
  - virtio devices are found by PCI enumeration and need virtio-pci ([virtio 1.3 spec §4.1](https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html)).
  - `microvm` avoids PCI by using virtio-mmio, but its devices are still described via ACPI or kernel command line, not a DT.
  - For test exits, QEMU's `isa-debug-exit` works without ACPI [host].
- **AArch64 on virt: devicetree by default**, with ACPI when booted through UEFI and `acpi=on`.
  - The DTB from QEMU 11.1.2 under HVF lists `arm,gic-v3`, `arm,armv8-timer`, `arm,pl011`, `pci-host-ecam-generic`, 32 × `virtio,mmio`, and `psci` (`method = "hvc"`) [host].
  - Power-off and CPU start go through PSCI `SYSTEM_OFF` / `CPU_ON` ([PSCI DEN0022](https://developer.arm.com/documentation/den0022/latest)).
  - Parsing a flattened DT is a self-contained job: a fixed header plus a structure block of tokens ([Devicetree spec](https://www.devicetree.org/specifications/)).
- **RISC-V on virt: devicetree by default**, with ACPI available (QEMU `acpi=on` default, used when booted through UEFI).
  - The DTB lists `riscv,clint0`, `riscv,plic0`, `ns16550a`, `pci-host-ecam-generic`, 8 × `virtio,mmio`, and `syscon-poweroff`/`syscon-reboot` over a `sifive,test` device [host].
  - Shutdown can use the SBI SRST extension or the syscon device.
  - The SBI spec says hardware discovery is out of its scope, so "supervisor software should use Device Tree or ACPI" ([SBI intro](https://github.com/riscv-non-isa/riscv-sbi-doc/blob/master/src/intro.adoc)).

**Version 1 implication (fact, not decision).** On QEMU, x86-64 means ACPI and the other two mean devicetree. Whichever architecture comes first, a Version 1 Nova needs both a DT parser and at least static ACPI table parsing.

---

## 8. Debugger support

- The QEMU gdbstub (`-s -S`, or `-gdb tcp::PORT`) lets you inspect registers and memory and set breakpoints and watchpoints. Under TCG it advertises unlimited hardware breakpoints and watchpoints. With other accelerators, support "will depend on if support has been added" ([QEMU gdb](https://www.qemu.org/docs/master/system/gdb.html)).
- **Verified [host]:**
  - Apple `lldb` (`gdb-remote PORT`) attaches to the gdbstub and disassembles for all three architectures.
  - Under **HVF**, attach and **instruction single-step** work. The stepped PC advanced through edk2 code.
- Homebrew's `gdb` 18.1 formula has an arm64 Sequoia bottle and is configured with `--enable-targets=all`, so one gdb covers all three ([formula](https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/g/gdb.rb)). It is not installed on the host. The installed `x86_64-elf-gdb` supports only `i386*`/`i8086` targets [host].
- x86 real-mode debugging is awkward with lldb (§3). With a Limine or UEFI entry it never comes up.

---

## 9. Toolchain maturity on the host

- **Apple clang 17** (`-print-targets`): aarch64/arm64, x86, x86-64. It has **no RISC-V backend**. `--target=riscv64-unknown-none-elf` fails with "No available targets are compatible" [host]. It compiled C23 freestanding objects for `x86_64-unknown-none-elf` and `aarch64-unknown-none-elf` [host].
- **Homebrew LLVM 23.1.4** (already installed): riscv64 (plus aarch64, x86-64). It compiled `-std=c23 -march=rv64gc -mabi=lp64d -mcmodel=medany` [host]. Homebrew LLD 23.1.4 links ELF for all three [host].
- **GCC cross toolchains** in Homebrew core: `x86_64-elf-gcc`, `aarch64-elf-gcc` and `riscv64-elf-gcc`, all 16.2.0 bottles [host: `brew info`]. xv6-riscv's Makefile expects a `riscv64-*-elf-` GNU prefix ([Makefile](https://github.com/mit-pdos/xv6-riscv/blob/riscv/Makefile)).
- **Implication.** With Homebrew LLVM, one compiler and linker serve all three architectures. Only RISC-V *requires* leaving Apple clang. The x86-64 and AArch64 back ends in LLVM and GCC are the most mature for kernel work; RISC-V is mainline in both and builds Linux and FreeBSD. Rust is out of scope (Nova is C23).

---

## 10. Learning material and reference kernels

| | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| Normative docs | Intel SDM (4 volumes, several thousand pages) + AMD APM. Lots of legacy to read past | Arm ARM DDI 0487 (very large) + GIC + PSCI + SMCCC specs. Arm's free "Learn the architecture" guides are good, short tutorials | Unprivileged + Privileged ISA manuals (privileged is short) + SBI spec, all open on GitHub |
| Teaching kernel | xv6 x86 is 32-bit and "we have stopped maintaining the x86 version of xv6, and switched our efforts to the RISC-V version" ([xv6-public README](https://github.com/mit-pdos/xv6-public)) | No xv6 port from MIT. Common tutorials target Raspberry Pi boards rather than QEMU `virt` | **xv6-riscv**: maintained, runs on QEMU `virt` with virtio-mmio disk, companion book and course ([xv6-riscv](https://github.com/mit-pdos/xv6-riscv), [MIT 6.1810](https://pdos.csail.mit.edu/6.1810/)) |
| Hobby/OSDev material | The largest body: the OSDev wiki and most hobby kernels and tutorials are x86-first ([OSDev wiki](https://wiki.osdev.org/), secondary) | Smaller. Much of it is board-specific (RPi) | Growing, smaller than x86. Most of it builds on QEMU `virt` + OpenSBI |
| Production reference kernels (reference, not authority) | Linux, FreeBSD, NetBSD/OpenBSD, SerenityOS | Linux, FreeBSD, NetBSD/OpenBSD | Linux, FreeBSD (separate SBI vs ELF entry points, per the QEMU source comment), NetBSD/OpenBSD |

The xv6 line is a direct match for the stated workflow: a Unix-like kernel in C on QEMU `virt` with virtio. The rows above about tutorial volume are judgements from familiarity, not measurements.

---

## 11. Cost summary per architecture (facts, no ranking)

**x86-64 first**

- Mandatory legacy setup before user mode: GDT, TSS (RSP0/IST), IDT, PIC masking, `SYSCALL` MSRs and `SWAPGS`. Without Limine, add a 32→64-bit trampoline, because QEMU `-kernel` is 32-bit only.
- SMP needs INIT-SIPI-SIPI plus a real-mode AP trampoline, unless Limine MP is used.
- Device discovery is ACPI, and a complete solution needs AML.
- Emulated (TCG) on the M4. It was the slowest configuration in the micro-benchmark.
- The most tutorial material exists, but the canonical teaching kernel (xv6 x86) is retired and 32-bit.

**AArch64 first**

- The only one of the three that runs **hardware-accelerated** on the M4 (HVF). Under HVF the gdbstub single-steps.
- HVF constraints: EL1 only in practice, GICv3 only, no ITS, no TrustZone, no 64K granule, 40-bit PA. TCG is available to exercise EL2/GICv2/64K.
- Clean exception model with banked stacks. The MMU is the most configuration-heavy of the three (MAIR/TCR/SCTLR, two TTBRs, barrier and TLB discipline).
- Devicetree discovery and PSCI make SMP and power-off simple.
- No xv6-class teaching kernel on QEMU `virt`. Spec documents are the largest.

**RISC-V 64 first**

- The smallest privileged architecture and the simplest paging format. Firmware (OpenSBI) already gives console, timer, IPI, hart start and reset through `ecall`.
- Devicetree discovery. A maintained, closely matching teaching kernel exists (xv6-riscv on QEMU `virt` + virtio-mmio).
- Emulated (TCG) on the M4. It was the fastest TCG configuration in the micro-benchmark.
- Needs Homebrew LLVM or GCC, not Apple clang.
- Pitfall: QEMU jumps to the ELF's lowest load address, so the linker script matters.
- Real hardware has more extension variance (Sstc/Svadu/AIA presence) than x86/Arm, but Nova's hardware bar is QEMU.

---

## 12. Open questions for the first-architecture ticket (#4)

These are inputs to grill on, not answers:

1. How much does hardware acceleration matter to the M0–M2 inner loop, given the measured TCG speeds?
2. Should the first architecture be the one with the least legacy (RISC-V), the one with acceleration and the cleanest exception model (AArch64), or the one with the most tutorials (x86-64)?
3. Should Limine be the single boot protocol across all three architectures from M0, or should each architecture start with its native QEMU `-kernel` path?
4. Should the second architecture be picked now? Picking it now would flush out arch-specific assumptions (devicetree vs ACPI, single vs split page-table roots) before they harden into the arch-independent core.

---

## Sources

**Specs and manuals**
- Intel 64 and IA-32 Architectures Software Developer's Manuals: https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- Arm Architecture Reference Manual for A-profile (DDI 0487): https://developer.arm.com/documentation/ddi0487/latest
- Arm GICv3/v4 Architecture Specification (IHI 0069): https://developer.arm.com/documentation/ihi0069/latest
- Arm PSCI (DEN0022): https://developer.arm.com/documentation/den0022/latest
- Arm Learn the architecture guides: memory management https://developer.arm.com/documentation/101811/latest, exception model https://developer.arm.com/documentation/102412/latest, generic timer https://developer.arm.com/documentation/102379/latest, GIC https://developer.arm.com/documentation/198123/latest
- RISC-V ISA manuals (unprivileged + privileged): https://github.com/riscv/riscv-isa-manual/releases
- RISC-V SBI specification: https://github.com/riscv-non-isa/riscv-sbi-doc
- OpenSBI: https://github.com/riscv-software-src/opensbi
- Devicetree specification: https://www.devicetree.org/specifications/
- UEFI and ACPI specifications: https://uefi.org/specifications
- Virtio 1.3: https://docs.oasis-open.org/virtio/virtio/v1.3/virtio-v1.3.html
- psABIs: https://gitlab.com/x86-psABIs/x86-64-ABI, https://github.com/ARM-software/abi-aa, https://github.com/riscv-non-isa/riscv-elf-psabi-doc

**QEMU**
- Introduction / accelerators: https://www.qemu.org/docs/master/system/introduction.html
- Arm `virt`: https://www.qemu.org/docs/master/system/arm/virt.html
- RISC-V `virt`: https://www.qemu.org/docs/master/system/riscv/virt.html
- x86 `microvm`: https://www.qemu.org/docs/master/system/i386/microvm.html
- GDB usage: https://www.qemu.org/docs/master/system/gdb.html
- Source, x86 PVH/Multiboot loading: https://github.com/qemu/qemu/blob/master/hw/i386/x86-common.c
- Source, RISC-V kernel loading (low address, not `e_entry`): https://github.com/qemu/qemu/blob/master/hw/riscv/boot.c
- HVF vGIC + nested virtualization patch series: https://patchew.org/QEMU/20260306130107.35359-1-mohamed@unpredictable.fr

**Apple**
- Hypervisor.framework, Apple silicon (EL2 and GIC APIs): https://developer.apple.com/documentation/hypervisor/apple-silicon
- Developer forum, EL2 enable report: https://developer.apple.com/forums/thread/775546

**Boot protocols**
- Limine boot protocol: https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md
- Limine (supported architectures and firmware): https://github.com/Limine-Bootloader/Limine
- Linux arm64 booting (reference): https://docs.kernel.org/arch/arm64/booting.html
- Linux RISC-V boot (reference): https://docs.kernel.org/arch/riscv/boot.html

**Reference / teaching kernels**
- xv6-riscv: https://github.com/mit-pdos/xv6-riscv
- xv6 x86 (unmaintained): https://github.com/mit-pdos/xv6-public
- MIT 6.1810: https://pdos.csail.mit.edu/6.1810/
- OSDev wiki (secondary): https://wiki.osdev.org/

**Tooling**
- Homebrew gdb formula: https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/g/gdb.rb
- ACPICA: https://www.intel.com/content/www/us/en/developer/topic-technology/open/acpica/overview.html
- uACPI: https://github.com/uACPI/uACPI
