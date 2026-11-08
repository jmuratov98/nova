# Research: what Limine gives the kernel, and how a boot image is built

Research for [issue #3](https://github.com/jmuratov98/nova/issues/3), part of the
[First process tree map](https://github.com/jmuratov98/nova/issues/1).
This note reports facts. It makes no decisions.

**Researched on 2026-11-08 against:**

| Thing | Version | Where |
|---|---|---|
| Limine bootloader | **v12.9.6**, released 2026-10-27 (the latest release) | [Limine releases][rel] |
| Limine boot protocol spec and `limine.h` | `limine-protocol` commit `6e85ddd` (2026-10-27), the commit Limine v12.9.6 itself pins | [PROTOCOL.md][P], [bootstrap][boot] |
| Official C template | `limine-c-template` commit `b279a3a` (2026-10-28) | [template][T] |
| QEMU | Homebrew 11.1.3 (11.1.2 installed on the host) | [formula][hb-qemu] |
| Ubuntu | 24.04 "noble" (the `ubuntu-latest` runner) and 26.04 "resolute" (the `ubuntu-26.04` runner) | [runner images][gha] |

Tags such as **[P]** link to the sources listed at the end. A claim marked
**(local)** comes from a read-only check on the development host (Apple M4,
macOS 15.6). A claim marked **(inference)** is my reading of the sources, not
something a source states. The [Unconfirmed](#unconfirmed) section lists what
I couldn't confirm.

---

## 1. Key facts

- **Every architecture is entered in 64-bit mode with paging on, in the higher half.**
  The kernel's segments are mapped at or above `0xffffffff80000000`, and the bootloader provides
  a higher-half direct map (HHDM) of physical memory at an offset the kernel must ask for
  [P §Memory Layout at Entry][P-layout].
- **The kernel runs at kernel privilege**: x86-64 long mode, ring 0 (CS = `0x28`, the 64-bit code
  descriptor); AArch64 EL1, or EL2 with VHE when the firmware leaves the CPU at EL2 and VHE exists;
  RISC-V Supervisor mode [P §Machine State at Entry][P-state].
- **Interrupts are masked and there's no trap table.** The kernel must install its own IDT,
  `VBAR_EL1` or `stvec` [P-state].
- **Stack:** at least 64 KiB in bootloader-reclaimable memory. The Stack Size feature can request
  another size. The return address is 0, so the entry point must not return [P-state].
- **Requests are static structures in the kernel image** (C structs with magic IDs).
  The bootloader fills in a `response` pointer for each one it supports. The latest base revision
  is **6**, which Limine v12.9.6 supports. AArch64 refuses anything below 6 [P §Base Revisions][P-base], [src-rev].
- **The initramfs can be a Limine *module***: `module_path:` in `limine.conf`, returned through
  the Module feature as a 4 KiB-aligned `struct limine_file` [CONFIG][C-limine], [P §Module Feature][P-mod].
- **Firmware:** x86-64 boots under BIOS (SeaBIOS, QEMU's default) or UEFI. Limine's AArch64 and
  RISC-V ports are **UEFI only** [README][R]. Homebrew QEMU ships edk2 UEFI images for all three
  architectures (local). Ubuntu ships them as separate packages: `ovmf`, `qemu-efi-aarch64` and
  `qemu-efi-riscv64` ([§5.1](#51-firmware-packages-per-host)).
- **Image tools:** an ISO needs `xorriso`. A GPT/FAT disk image needs `sgdisk` and `mtools`.
  The `limine` CLI is only needed on x86 to install the BIOS boot code (`limine bios-install`)
  [USAGE][U-iso], [T-mk]. All are in Homebrew. Ubuntu has `xorriso`, `mtools` and `gdisk`,
  but **no `limine` package**.
- **Versioning:** SemVer since 7.x [R]. Major versions come often (10.0.0 in 2025-09,
  11.0.0 in 2026-03, 12.0.0 in 2026-04) [CL]. GitHub releases are immutable and GPG-signed.
  The protocol header lives in a separate repo with no tags, so it's pinned by commit [rel], [boot].

---

## 2. Machine state at kernel entry

All rows are from [P §Machine State at Entry][P-state] and [P §Caching][P-cache] unless noted.
"BR" means base revision. Rows marked BR6 apply when the kernel requests base revision 6.

| | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| CPU mode / privilege | Long mode: `CR0.PE/PG/WP`, `CR4.PAE`, `EFER.LME/LMA` set, `EFER.NX` if available. CS = `0x28` (64-bit code), DS/ES/SS/FS/GS = `0x30`. BR5+: all other `CR0`/`CR4`/`EFER` bits cleared | Little-endian AArch64. BR6: EL2 with VHE if the bootloader runs at EL2 and VHE is supported, otherwise EL1. Never EL2 without VHE. BR < 6: always EL1 | Supervisor mode |
| Entry point | ELF entry, or the Entry Point feature | same | same; `t0` also holds the entry address |
| Interrupts | `RFLAGS.IF` = 0. BR5+: `RFLAGS` = `0x2`. Legacy PICs masked. I/O APIC entries masked. BR5+: LAPIC enabled and its LVT entries masked | `PSTATE.{D,A,I,F}` = 1. BR6: other `PSTATE` fields 0 | `sie` = 0. BR6: `sstatus` = `0x200000000` (only `UXL` = 2), so `SIE` = 0 |
| Trap table | IDT undefined. BR5+: IDTR base 0, limit 0 | `VBAR_EL1` undefined | BR6: `stvec` = 0. Earlier: undefined |
| Descriptor tables | GDT (in bootloader-reclaimable memory) with null, 16-, 32- and 64-bit code/data descriptors. BR5+: no TSS (TR base 0, limit 0), no LDT | n/a | n/a |
| FP / SIMD | Protocol ABI is SysV *without* FP/SIMD [P-notes]. BR5+ clears the other `CR4` bits, so `OSFXSR` is clear **(inference: SSE faults until the kernel enables it)** | BR6: `CPACR_EL1` = 0. The kernel must enable FP/SIMD/SVE before using it | BR6: `sstatus.FS/VS` = 0. The kernel must enable them before FP or vector instructions |
| Paging | 4-level by default. 5-level (LA57) if requested and available | MMU and caches on. 4 KiB granule for `TTBR0`/`TTBR1`. `T0SZ`/`T1SZ` = 16 (4-level) or 12 (5-level, with `TCR_EL1.DS` = 1). `TTBR1_EL1` holds the higher-half tables. `TTBR0_EL1` is free for the kernel (BR ≥ 1) | `satp` set to the requested mode (**Sv48 by default**, Sv39 minimum, Sv57 optional). BR6: ASID = 0 |
| Memory types | PAT: PAT0 WB, PAT1 WT, PAT2 UC-, PAT3 UC, PAT4 WP, PAT5 WC. Kernel and HHDM are WB, framebuffer WC. MTRRs as firmware left them | BR4+: `MAIR_EL1.Attr0` = `0xff` (normal WB), `Attr1` = framebuffer type, the rest unused | PBMT = PMA everywhere. Framebuffer `PBMT=NC` if `Svpbmt` exists |
| Stack | `rsp` → top of a stack of at least 64 KiB in bootloader-reclaimable memory. A return address of 0 is pushed | `SP` likewise. `X30` (LR) = 0 | `sp` likewise. `ra` = 0. `gp` = 0, so the kernel loads its own |
| Other registers | All other GPRs 0 | All other GPRs 0 | All other GPRs 0 |
| Firmware | UEFI boot services exited (if booted by UEFI). A20 open | UEFI boot services exited | UEFI boot services exited |
| x86-only extras | BR5+: VT-d and AMD-Vi IOMMUs disabled unless the "Keep IOMMU" feature is requested | | |

Notes:

- The protocol's C ABIs are SysV x86-64 without FP/SIMD, AAPCS64 without FP/SIMD, and LP64
  soft-float for RISC-V. The kernel may use FP/SIMD internally, but not across the protocol
  boundary [P-notes].
- The template compiles accordingly: `-mno-sse -mno-mmx -mno-red-zone -mcmodel=kernel` on x86-64,
  `-march=armv8-a+nofp+nosimd` on AArch64, and `-mabi=lp64 -march=rv64imac…` on RISC-V
  [T-kmk].
- AArch64 at EL2: `HCR_EL2` = `E2H|TGE|RW|SWIO`, `CPTR_EL2` = 0, and the `*_EL12` registers are
  undefined. The `*_EL1` guarantees still apply through VHE redirection [P-state].
- **(inference)** On QEMU `virt`, `virtualization=off` is the default [qemu-arm], so the firmware
  doesn't run at EL2 and Limine enters the kernel at EL1. The template's `-cpu cortex-a72` is
  Armv8.0, which has no VHE (FEAT_VHE arrived in Armv8.1), so even with `virtualization=on` the
  kernel would be entered at EL1.

## 3. Memory layout and the higher-half direct map

From [P §Memory Layout at Entry][P-layout] and [P §Base Revision Changes Summary][P-base]:

- **Kernel placement.** Segments are mapped at or above `0xffffffff80000000`. A non-relocatable
  kernel must already be linked there; the template links at exactly `0xffffffff80000000` on every
  architecture [T-lds]. The image is physically contiguous with one uniform virtual-to-physical
  offset. The Executable Address feature reports `physical_base` and `virtual_base`.
- **ELF permissions are honoured**: `PF_X` controls execute and `PF_W` controls write.
  On x86-64, execute protection depends on NX.
- **KASLR** is off by default (since 10.0.0) and only applies to relocatable kernels
  (`kaslr: yes`) [CL], [C-limine].
- **HHDM.** The offset comes from the HHDM feature. It is chosen by the bootloader, may vary
  between boots and must not be hard-coded. It is randomised by default only when KASLR is on
  (`randomise_hhdm_base`) [P-layout], [C-limine].
- **What the HHDM covers (BR ≥ 4, so BR6 too):** memory-map regions of type usable,
  bootloader-reclaimable, executable-and-modules, framebuffer, reserved-mapped, ACPI-reclaimable
  and ACPI-NVS. Since BR3 there is **no unconditional map of the first 4 GiB**, and since BR1
  there is **no identity map** [P-base].
  **(inference)** MMIO that isn't in one of those regions isn't mapped, for example a PL011 or
  16550 UART on AArch64/RISC-V `virt`. The kernel must map it itself. x86 COM1 uses port I/O and
  needs no mapping.
- **Pointers in responses are HHDM virtual addresses** unless noted (BR6 reports RSDP, SMBIOS and
  the EFI system table as HHDM addresses too). All responses live in bootloader-reclaimable memory
  [P-notes], [P-base].
- **Bootloader page tables** are in bootloader-reclaimable memory, with an undefined layout
  [P-layout].

## 4. What can be requested

Mechanics [P §Features][P-feat], [P §Requests Delimiters][P-delim]:

- A request is a struct with `uint64_t id[4]` (the common magic plus 2 feature words), a `revision`
  and a `response` pointer. It is 8-byte aligned, appears at most once, and lives in the loaded
  image. The bootloader sets `response` if it handled the request, and leaves it NULL otherwise.
- Requests between a `LIMINE_REQUESTS_START_MARKER` and a `LIMINE_REQUESTS_END_MARKER` are the
  only ones honoured when markers are present (BR ≥ 2). The base-revision tag
  `LIMINE_BASE_REVISION(6)` is checked with `LIMINE_BASE_REVISION_SUPPORTED()`.
- The template marks the request variables `volatile` and `__attribute__((used))`, puts them in a
  `.limine_requests` section, and gives that section its own `PT_LOAD` [T-main], [T-lds].
- **(source observation)** Limine scans the image only up to the start of the trailing
  zero-filled part of the last segment (`image_size_before_bss`), so requests must be initialised
  data, not `.bss` [src-scan], [src-elf].

Features relevant to the questions in the ticket (full list in [P §Feature List][P-list]):

| Need | Feature | What comes back | Arch notes |
|---|---|---|---|
| Memory map | Memory Map | Sorted array of `{base, length, type}`. Types: usable, reserved, ACPI reclaimable/NVS, bad, bootloader-reclaimable, executable-and-modules, framebuffer, reserved-mapped. Usable and bootloader-reclaimable entries are 4 KiB aligned and never overlap | all |
| Raw UEFI map | EFI Memory Map | The UEFI map (HHDM pointer), descriptor size and version | UEFI only |
| HHDM offset | HHDM | `offset` | all |
| Kernel address | Executable Address | `physical_base`, `virtual_base` | all |
| Kernel file / cmdline | Executable File, Executable Command Line | `struct limine_file` of the kernel, and the `cmdline:` string | all |
| Initramfs and other files | Module | Array of `struct limine_file` (`address` 4 KiB aligned, `size`, `path`, `string`, media/partition info). No response if no module loaded. Request revision 1 adds *internal modules* named by the kernel itself (with a `REQUIRED` flag). Revision 2 adds bootloader-side gzip decompression (`COMPRESSED`) | all |
| Framebuffer | Framebuffer | Array of framebuffers (address, width, height, pitch, bpp, RGB masks, EDID, video modes). No response if none | all; on QEMU `virt` the template adds `-device ramfb` [T-mk] |
| ACPI | RSDP | RSDP address (HHDM in BR6). No response without ACPI | all |
| SMBIOS | SMBIOS | 32- and 64-bit entry points | all |
| Device tree | DTB | HHDM pointer to the DTB. `memory@` nodes are removed and `/chosen` should be ignored. No response if no DTB | typically AArch64/RISC-V |
| UEFI | EFI System Table | System table pointer | UEFI only |
| SMP | MP | BSP ID and an array of `limine_mp_info`. APs are started **only if this request is present**, then parked until the kernel writes `goto_address`. IDs: x86 LAPIC ID (x2APIC optional), AArch64 MPIDR, RISC-V hart ID | per arch |
| Boot hart | RISC-V BSP Hart ID | `bsp_hartid` without starting APs | RISC-V only |
| Paging mode | Paging Mode | Choose and bound the mode (`mode`, `min_mode`, `max_mode`) | x86 4/5-level, AArch64 4/5-level, RISC-V Sv39/48/57 |
| Stack size | Stack Size | Sets the BSP and AP stack size | all |
| Misc. | Bootloader Info, Firmware Type (`X86BIOS`, `EFI32`, `EFI64`, `SBI`), Date at Boot (UNIX time from RTC), TSC Frequency (`rdtsc` / `CNTPCT_EL0` / `rdtime`), Entropy, TPM Event Log, Bootloader Performance, Flanterm FB init params, Entry Point, x86-64 Keep IOMMU | | |

There is **no console or terminal-write feature** in the current list. Output (serial or
framebuffer) is up to the kernel. Flanterm FB init params only describes how Limine set up its own
terminal [P-list].

`limine.conf` for a Limine-protocol kernel [C-limine], [C-loc], [C-paths]:

```
timeout: 0

/Nova
    protocol: limine
    path: boot():/boot/kernel
    cmdline: ...
    module_path: boot():/boot/initramfs
    module_string: initramfs
```

- Global options must come before the first entry.
- Limine looks for the config at `<EFI app dir>/limine.conf` (UEFI), then `/boot/limine/limine.conf`,
  `/boot/limine.conf`, `/limine/limine.conf` and `/limine.conf`.
- `boot():` means the partition that holds the config.
- A `$` prefix on a path means "gunzip transparently". A `#<blake2b>` suffix means "verify this hash".

## 5. Firmware in QEMU

| | x86-64 | AArch64 | RISC-V 64 |
|---|---|---|---|
| Limine ports that run here | BIOS (`limine-bios*.bin/.sys`), UEFI x86-64 (`BOOTX64.EFI`), UEFI IA-32 (`BOOTIA32.EFI`) [U-iso], [T-mk] | UEFI only (`BOOTAA64.EFI`) [R] | UEFI only (`BOOTRISCV64.EFI`) [R] |
| QEMU machine used by the template | `-M q35` [T-mk] | `-M virt -cpu cortex-a72` [T-mk] | `-M virt -cpu rv64` [T-mk] |
| QEMU default firmware | SeaBIOS [qemu-x86] | None stated in QEMU docs; the template always passes UEFI in pflash (see [Unconfirmed](#unconfirmed)) | OpenSBI as `-bios` (M-mode). edk2 goes in **pflash0** (S-mode code, must be exactly **32 MiB**) and pflash1 holds variables [qemu-rv] |
| How the template passes UEFI | `-drive if=pflash,unit=0,format=raw,file=ovmf-code-x86_64.fd,readonly=on` (no vars drive) [T-mk] | same, with `ovmf-code-aarch64.fd` | same, with `ovmf-code-riscv64.fd` |
| Where the template gets UEFI | `osdev0/edk2-ovmf-stable-bins`, `releases/latest`: CI-built images from the latest edk2 stable tag (latest release `20261026T212116Z`) [ovmf-bins] | same | same |

Limine's own test suite boots every port under QEMU **9.2 or later**, using UEFI images from
`osdev0/edk2-ovmf-stable-bins` [I].

### 5.1 Firmware packages per host

**Homebrew QEMU (macOS).** On this host it's 11.1.2; the current formula is 11.1.3 [hb-qemu].
It ships these files in `$(brew --prefix qemu)/share/qemu` **(local)**:

| Arch | Code | Vars template | Size of code image |
|---|---|---|---|
| x86-64 BIOS | `bios-256k.bin` (SeaBIOS) | n/a | 256 KiB |
| x86-64 UEFI | `edk2-x86_64-code.fd` (also `edk2-x86_64-secure-code.fd`) | `edk2-i386-vars.fd` | 3.5 MiB |
| AArch64 UEFI | `edk2-aarch64-code.fd` | `edk2-arm-vars.fd` | 64 MiB |
| RISC-V UEFI | `edk2-riscv-code.fd` | `edk2-riscv-vars.fd` | 32 MiB (the size QEMU requires) |
| RISC-V M-mode | `opensbi-riscv64-generic-fw_dynamic.bin` | n/a | |

- The vars templates are the ones named in the `share/qemu/firmware/60-edk2-*.json` descriptors
  **(local)**.
- QEMU's bundled edk2 binaries were last updated to **edk2-stable202408** (QEMU commit
  `065e2ecf79`). The `pc-bios/README` text still says 202302 [qemu-edk2].

**Ubuntu.** None of these packages is preinstalled on the `ubuntu-24.04` runner image; its
README lists no QEMU, OVMF, xorriso or mtools [gha-2404].

| Package | 24.04 noble | 26.04 resolute | Firmware files |
|---|---|---|---|
| `qemu-system-x86` | 1:8.2.2+ds-0ubuntu1.16 (1.18 in noble-updates). Depends `seabios`, recommends `ovmf` [u-n-x86] | 1:10.2.1+ds-1ubuntu3. Same dependencies [u-r-x86] | |
| `qemu-system-arm` (has `qemu-system-aarch64`) | 1:8.2.2+ds-0ubuntu1.16. Recommends `qemu-efi-aarch64` [u-n-arm] | 1:10.2.1+ds-1ubuntu3. Same [u-r-arm] | |
| RISC-V QEMU | in **`qemu-system-misc`** (1:8.2.2…). OpenSBI blob in `qemu-system-data` at `/usr/share/qemu/opensbi-riscv64-generic-fw_dynamic.bin` [u-n-misc], [u-n-data] | in new **`qemu-system-riscv`** (1:10.2.1…). Depends `opensbi`, recommends `qemu-efi-riscv64` [u-r-rv] | |
| `ovmf` | 2024.02-2ubuntu0.10 [u-n-ovmf] | 2025.11-3ubuntu7.3, now a metapackage over `ovmf-generic` and others [u-r-ovmf] | `/usr/share/OVMF/OVMF_CODE_4M.fd`, `OVMF_VARS_4M.fd`, `/usr/share/ovmf/OVMF.fd` [u-n-ovmf-f], [u-r-ovmfg-f] |
| `qemu-efi-aarch64` | 2024.02-2ubuntu0.10 [u-n-aa] | 2025.11-3ubuntu7.3 [u-r-aa] | `/usr/share/AAVMF/AAVMF_CODE.fd`, `AAVMF_VARS.fd`, `/usr/share/qemu-efi-aarch64/QEMU_EFI.fd` [u-n-aa-f] |
| `qemu-efi-riscv64` | 2024.02-2ubuntu0.10, **universe** [u-n-rv] | 2025.11-3ubuntu7.3, main [u-r-rvefi] | `/usr/share/qemu-efi-riscv64/RISCV_VIRT_CODE.fd`, `RISCV_VIRT_VARS.fd` [u-n-rv-f] |

Noble's QEMU (8.2.2) is older than the 9.2 that Limine's own checks require [I]. Whether Limine
12.x boots under it is unconfirmed.

## 6. Building a bootable image

### 6.1 Tools

| Tool | Needed for | Homebrew | Ubuntu noble | Ubuntu resolute |
|---|---|---|---|---|
| Limine binaries (`BOOT*.EFI`, `limine-uefi-cd.bin`, `limine-bios-cd.bin`, `limine-bios.sys`) | every image | `limine` 12.9.6 formula, built from the release tarball with `--enable-all` using Homebrew LLVM, LLD, nasm and mtools; bottled for `arm64_sequoia` [hb-limine], [hb-limine-rb] | **no package** [u-n-lim] | **no package** [u-r-lim] |
| …or the release asset `limine-binary.tar.gz` | every image | n/a: download from GitHub | same | same |
| `limine` CLI (`bios-install`, `enroll-config`, `--print-datadir`, `version`) | x86 BIOS boot only, plus Secure Boot config enrolment | in the `limine` formula; or built from `limine.c` in the binary tarball with any C99 compiler (`make`) [R], [bin] | build from the tarball | same |
| `xorriso` | ISO images | 1.5.8.pl02 [hb-xorriso]. Installed on this host **(local)** | 1:1.5.6-1.1ubuntu3 [u-n-xor] | 1:1.5.6-1.1ubuntu4 [u-r-xor] |
| `mtools` (`mformat`, `mmd`, `mcopy`) | FAT disk images | 4.0.50 [hb-mtools]. Not installed **(local)**. Conflicts with the `multimarkdown` and `mcat` formulae (both install binaries of the same names) **(local, `brew info`)** | 4.0.43-1build1 [u-n-mt] | 4.0.49-1 [u-r-mt] |
| `sgdisk` | GPT disk images (template's `all-hdd`) | `gptfdisk` 1.0.10 [hb-gpt]. Not installed **(local)** | `gdisk` 1.0.10-1build1 [u-n-gd] | `gdisk` 1.0.10-2build1 [u-r-gd] |

The binary tarball for v12.9.6 contains: `BOOTX64.EFI`, `BOOTIA32.EFI`, `BOOTAA64.EFI`,
`BOOTRISCV64.EFI`, `BOOTLOONGARCH64.EFI`, `limine-uefi-cd.bin`, `limine-bios-cd.bin`,
`limine-bios-pxe.bin`, `limine-bios.sys`, `limine.c` with a POSIX `Makefile`, and a Windows
`limine.exe`. It does **not** contain `limine.h` [bin] **(local listing)**.

`limine.h` (0BSD) comes from the `limine-protocol` repo, or from the `limine-protocol/` directory in
the source tarball [P], [src-tar] **(local listing)**.

### 6.2 Minimal steps: kernel ELF → bootable ISO

From [USAGE §BIOS/UEFI hybrid ISO creation][U-iso] and the template's `$(IMAGE_NAME).iso` rule
[T-mk]:

```sh
mkdir -p iso_root/boot/limine iso_root/EFI/BOOT
cp kernel.elf                    iso_root/boot/kernel
cp limine.conf limine-binary/limine-uefi-cd.bin iso_root/boot/limine/
# x86-64 only: BIOS boot files
cp limine-binary/limine-bios.sys limine-binary/limine-bios-cd.bin iso_root/boot/limine/
# per arch: BOOTX64.EFI (+BOOTIA32.EFI) | BOOTAA64.EFI | BOOTRISCV64.EFI
cp limine-binary/BOOTX64.EFI     iso_root/EFI/BOOT/

# The "-b ... -boot-info-table" line is for x86-64 BIOS only; drop it on AArch64 and RISC-V.
xorriso -as mkisofs -R -r -J \
    -b boot/limine/limine-bios-cd.bin -no-emul-boot -boot-load-size 4 -boot-info-table \
    -hfsplus -apm-block-size 2048 \
    --efi-boot boot/limine/limine-uefi-cd.bin -efi-boot-part --efi-boot-image \
    --protective-msdos-label iso_root -o nova.iso

limine-binary/limine bios-install nova.iso   # x86-64 BIOS only
```

Run it, as the template's `run` target does [T-mk]. Firmware paths below are Homebrew's; on Ubuntu,
use the `/usr/share/...` paths from §5.1:

```sh
# x86-64, UEFI          (drop the -drive line to boot SeaBIOS instead)
qemu-system-x86_64 -M q35 -m 2G -cdrom nova.iso \
  -drive if=pflash,unit=0,format=raw,file=$(brew --prefix qemu)/share/qemu/edk2-x86_64-code.fd,readonly=on
# AArch64
qemu-system-aarch64 -M virt -cpu cortex-a72 -m 2G -device ramfb -cdrom nova.iso \
  -drive if=pflash,unit=0,format=raw,file=$(brew --prefix qemu)/share/qemu/edk2-aarch64-code.fd,readonly=on
# RISC-V 64
qemu-system-riscv64 -M virt -cpu rv64 -m 2G -device ramfb -cdrom nova.iso \
  -drive if=pflash,unit=0,format=raw,file=$(brew --prefix qemu)/share/qemu/edk2-riscv-code.fd,readonly=on
```

The template also adds `-device qemu-xhci -device usb-kbd -device usb-mouse`, which a serial-only
test doesn't need [T-mk]. Serial output to stdout would be `-serial stdio` or `-nographic`. That's
standard QEMU usage, not something the Limine sources cover.

### 6.3 Alternative: a GPT disk image with a FAT partition

The template's `all-hdd` rule [T-mk]:

1. `dd` a 64 MiB file.
2. `sgdisk -n 1:… -t 1:ef00` (plus `-m 1` on x86 for a hybrid MBR).
3. `limine bios-install` (x86 only).
4. `mformat -i img@@offset`.
5. `mmd` the `/EFI/BOOT` and `/boot/limine` directories.
6. `mcopy` the kernel, `limine.conf`, `limine-bios.sys` (x86) and the `BOOT*.EFI` files.

Boot it with `-hda`. Limine reads FAT12/16/32 and ISO9660 only [R].

### 6.4 Per-architecture differences

**(inference from the template and USAGE)** AArch64 and RISC-V images need only the
`BOOT*.EFI` and `limine-uefi-cd.bin` files and a tool to write the image. They need no `limine`
CLI and no BIOS files.

### 6.5 Compiler side (local)

These are observations on the host, outside Limine's own sources.

- The template builds with Clang using `-target <arch>-unknown-none-elf` and `-fuse-ld=lld`
  [T-kmk].
- Apple clang 17 on this host registers only the AArch64, ARM and x86 targets. It has **no
  RISC-V backend** **(local, `clang -print-targets`)**.
- Homebrew `llvm` (keg-only, 23.1.4 installed; formula 23.1.5 [hb-llvm]) at `/opt/homebrew/opt/llvm`
  does include `riscv64` **(local)**. `ld.lld` is Homebrew LLD 23.1.4 **(local)**.

## 7. Versioning, pinning and vendoring

**Versioning and releases:**

- **SemVer since 7.x** [R]. A change that broke SemVer was reverted in 11.2.1 "to move on to
  12.x afterwards" [CL].
- **Major versions:** 7.0.0 2024-01, 8.0.0 2024-08, 9.0.0 2025-02, 10.0.0 2025-09, 11.0.0 2026-03,
  12.0.0 2026-04. There were 26 releases in the 12.x line between 2026-04-25 and 2026-10-27 [CL], [rel].
- Major versions have dropped protocol support before. 11.0.0 dropped base revisions 0–3 on x86
  and everything except 6 on the other ports. 11.1.0 walked that back except on AArch64, which still
  requires base revision 6 [CL], [src-rev].
- **Old majors:** no older-major releases appear after the next major ships. The last 11.x release
  (11.4.1) came before 12.0.0 [rel]. I found no stated support policy.

**Where releases live:**

- **Repository:** Limine moved to GitHub (`Limine-Bootloader/Limine`) in 11.3.1. The Codeberg repo
  is archived ("Moved to GitHub") and its last release is v11.2.1 [CL], [cb].
- **Branches and tags:** each major has a branch (`v12.x` is the default). Releases are tags `vX.Y.Z`
  [gh-branches]. Until 11.x, binaries were committed to `vN.x-binary` branches. **Since 12.0.0 they
  ship only as release assets** [CL].
- **Release assets** [rel]:
  - Source tarballs `limine-X.Y.Z.tar.{gz,bz2,xz}` bundle their dependencies, including
    `limine-protocol`.
  - `limine-binary.tar.{gz,xz}` and `limine-binary.zip` are unversioned names since 12.0.2.
  - Every asset has a `.sig` GPG signature, key `05D29860D0A0668AAEFB9D691F3C021BECA23821`.
  - GitHub marks every release immutable. The 12.0.1 note: "fixed assets that cannot be amended
    into 12.0.0 afterwards due to release immutability".
  - The `limine-12.9.6.tar.gz` sha256 is
    `5022d02c0709ccf3cd6702e89206e2e8c953d253d80fc05b276a526c23719332`. It matches the Homebrew
    formula **(local)**, [hb-limine-rb].
- **Protocol header:** `limine-protocol` has **no tags or releases** [P-repo]. Limine v12.9.6's
  `bootstrap` pins it by commit (`6e85ddd`). The C template pins the same commit [boot], [T-deps].

**How the official template pins:**

- It downloads `releases/latest/download/limine-binary.tar.gz` and `edk2-ovmf-bins.tar.gz`, so the
  bootloader and firmware are *unpinned* [T-mk].
- It pins `limine-protocol` and its freestanding header and runtime repos by commit hash [T-deps].

**Homebrew:** carries one current `limine` version. There is no versioned `limine@N` formula
(`formulae.brew.sh/api/formula/limine@11.json` returns 404) [hb-limine]. Pinning through Homebrew
therefore follows whatever Homebrew ships.

**Building from source:**

- Requires GNU make, nasm (for the x86 ports), mtools (for `limine-uefi-cd.bin`) and gcc or clang
  with binutils.
- Ports are opt-in through `./configure` [I].
- Homebrew's formula builds it on macOS with LLVM, LLD, nasm and mtools [hb-limine-rb].

## Unconfirmed

1. **QEMU AArch64 `virt` default firmware.** The QEMU docs don't say whether `virt` loads any
   firmware without `-bios` or pflash [qemu-arm]. Every example I found passes edk2 explicitly.
2. **Limine 12.x under Ubuntu noble's QEMU 8.2.2.** Limine documents only that its *test suite*
   needs QEMU ≥ 9.2 [I].
3. **Which firmware tables QEMU+edk2 exposes on AArch64 and RISC-V.** That is, whether Limine
   returns RSDP, DTB or both on `virt`. QEMU `riscv virt` generates ACPI tables by default and
   always generates a DTB [qemu-rv], but what edk2 passes on wasn't checked. Nothing was booted.
4. **Ubuntu's `RISCV_VIRT_CODE.fd` size.** QEMU requires exactly 32 MiB for pflash on RISC-V
   [qemu-rv]. Homebrew's image is 32 MiB (local), but Ubuntu's size wasn't checked.
5. **`universe` on GitHub runners.** Noble's `qemu-efi-riscv64` is in universe [u-n-rv]. I didn't
   confirm that universe is enabled on the runner image.
6. **Simpler image formats.** Booting Limine from QEMU's `vvfat` (`-drive file=fat:rw:dir`), or from
   an unpartitioned FAT image under OVMF, would avoid `xorriso`, `mtools` and `sgdisk`. Limine
   supports unpartitioned media [R], but neither path was checked.
7. **Limine's support policy for older major versions.** I found no statement. Only the release
   history is reported above.

---

## Sources

Limine bootloader (tag `v12.9.6` unless noted):

- [rel] — v12.9.6 release page (assets, signatures, signing key), https://github.com/Limine-Bootloader/Limine/releases/tag/v12.9.6
- [R] — README, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/README.md
- [I] — INSTALL.md, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/INSTALL.md
- [U-iso] — USAGE.md, hybrid ISO creation, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/USAGE.md#biosuefi-hybrid-iso-creation
- [C-loc], [C-limine], [C-paths] — CONFIG.md (config location, options, paths), https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/CONFIG.md
- [CL] — ChangeLog, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/ChangeLog
- [boot] — `bootstrap`, which pins `limine-protocol`, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/bootstrap#L66-L69
- [src-rev] — `SUPPORTED_BASE_REVISION 6` and the AArch64 minimum, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/protos/limine.c#L55
- [src-scan] — the request and base-revision scan, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/protos/limine.c#L705-L762
- [src-elf] — `image_size_before_bss` in the ELF loader, https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/lib/elf.c#L1203-L1257
- [bin] — binary tarball (contents listed locally), https://github.com/Limine-Bootloader/Limine/releases/download/v12.9.6/limine-binary.tar.gz
- [src-tar] — source tarball (contents listed locally), https://github.com/Limine-Bootloader/Limine/releases/download/v12.9.6/limine-12.9.6.tar.gz
- [gh-branches] — branches, https://github.com/Limine-Bootloader/Limine/branches/all
- [cb] — archived Codeberg repo, https://codeberg.org/Limine/Limine

Limine boot protocol (`limine-protocol` commit `6e85ddd6f928b5b512015c4d47d1cfce2fd28079`):

- [P] — PROTOCOL.md, https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md
- [P-notes], [P-delim], [P-base], [P-layout], [P-cache], [P-state], [P-feat], [P-list], [P-mod] — sections of the same file. The links go to the matching headings.
- [P-repo] — repository (no tags or releases), https://github.com/Limine-Bootloader/limine-protocol

Official C template (`limine-c-template` commit `b279a3af4f859006d7124682d21998b719d29d84`):

- [T] — repository at that commit, https://github.com/Limine-Bootloader/limine-c-template/tree/b279a3af4f859006d7124682d21998b719d29d84
- [T-mk] — top-level `GNUmakefile`. [T-kmk]: `kernel/GNUmakefile`. [T-lds]: `kernel/linker-scripts/`. [T-main]: `kernel/src/main.c`. [T-deps]: `kernel/get-deps`.
- [ovmf-bins] — `osdev0/edk2-ovmf-stable-bins` releases, https://github.com/osdev0/edk2-ovmf-stable-bins/releases

QEMU:

- [qemu-rv] — RISC-V `virt` docs, https://www.qemu.org/docs/master/system/riscv/virt.html
- [qemu-arm] — Arm `virt` docs (v11.1.2), https://github.com/qemu/qemu/blob/v11.1.2/docs/system/arm/virt.rst
- [qemu-x86] — x86 PC docs ("QEMU uses the PC BIOS from the Seabios project"), https://github.com/qemu/qemu/blob/v11.1.2/docs/system/target-i386-desc.rst.inc
- [qemu-edk2] — commit "update binaries to edk2-stable202408", https://github.com/qemu/qemu/commit/065e2ecf79

Homebrew:

- [hb-qemu] https://formulae.brew.sh/formula/qemu
- [hb-limine] https://formulae.brew.sh/formula/limine
- [hb-limine-rb] — formula source, https://github.com/Homebrew/homebrew-core/blob/36dcbfff1896bc9f9195a2a0a94e30b75639f65c/Formula/l/limine.rb
- [hb-xorriso] https://formulae.brew.sh/formula/xorriso
- [hb-mtools] https://formulae.brew.sh/formula/mtools
- [hb-gpt] https://formulae.brew.sh/formula/gptfdisk
- [hb-llvm] https://formulae.brew.sh/formula/llvm

Ubuntu, packages.ubuntu.com. Package pages are `https://packages.ubuntu.com/<suite>/<package>`; file lists are `https://packages.ubuntu.com/<suite>/<arch>/<package>/filelist`:

- noble: [u-n-x86], [u-n-arm], [u-n-misc] (file list), [u-n-data] (file list), [u-n-ovmf], [u-n-ovmf-f] (file list), [u-n-aa], [u-n-aa-f] (file list), [u-n-rv], [u-n-rv-f] (file list), [u-n-xor], [u-n-mt], [u-n-gd], [u-n-lim] ("No such package")
- resolute: [u-r-x86], [u-r-arm], [u-r-rv], [u-r-ovmf], [u-r-ovmfg-f] (file list), [u-r-aa], [u-r-rvefi], [u-r-xor], [u-r-mt], [u-r-gd], [u-r-lim] ("No such package")

GitHub Actions:

- [gha] — runner image labels, https://github.com/actions/runner-images#available-images
- [gha-2404] — Ubuntu 24.04 image README, https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md

[rel]: https://github.com/Limine-Bootloader/Limine/releases/tag/v12.9.6
[R]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/README.md
[I]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/INSTALL.md
[U-iso]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/USAGE.md#biosuefi-hybrid-iso-creation
[C-loc]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/CONFIG.md#location-of-the-config-file
[C-limine]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/CONFIG.md#options
[C-paths]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/CONFIG.md#paths
[CL]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/ChangeLog
[boot]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/bootstrap#L66-L69
[src-rev]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/protos/limine.c#L55
[src-scan]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/protos/limine.c#L705-L762
[src-elf]: https://github.com/Limine-Bootloader/Limine/blob/v12.9.6/common/lib/elf.c#L1203-L1257
[bin]: https://github.com/Limine-Bootloader/Limine/releases/download/v12.9.6/limine-binary.tar.gz
[src-tar]: https://github.com/Limine-Bootloader/Limine/releases/download/v12.9.6/limine-12.9.6.tar.gz
[gh-branches]: https://github.com/Limine-Bootloader/Limine/branches/all
[cb]: https://codeberg.org/Limine/Limine
[P]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md
[P-repo]: https://github.com/Limine-Bootloader/limine-protocol
[P-notes]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#general-notes
[P-delim]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#requests-delimiters
[P-base]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#base-revision-changes-summary
[P-layout]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#memory-layout-at-entry
[P-cache]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#caching
[P-state]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#machine-state-at-entry
[P-feat]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#features
[P-list]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#feature-list
[P-mod]: https://github.com/Limine-Bootloader/limine-protocol/blob/6e85ddd6f928b5b512015c4d47d1cfce2fd28079/PROTOCOL.md#module-feature
[T]: https://github.com/Limine-Bootloader/limine-c-template/tree/b279a3af4f859006d7124682d21998b719d29d84
[T-mk]: https://github.com/Limine-Bootloader/limine-c-template/blob/b279a3af4f859006d7124682d21998b719d29d84/GNUmakefile
[T-kmk]: https://github.com/Limine-Bootloader/limine-c-template/blob/b279a3af4f859006d7124682d21998b719d29d84/kernel/GNUmakefile
[T-lds]: https://github.com/Limine-Bootloader/limine-c-template/tree/b279a3af4f859006d7124682d21998b719d29d84/kernel/linker-scripts
[T-main]: https://github.com/Limine-Bootloader/limine-c-template/blob/b279a3af4f859006d7124682d21998b719d29d84/kernel/src/main.c
[T-deps]: https://github.com/Limine-Bootloader/limine-c-template/blob/b279a3af4f859006d7124682d21998b719d29d84/kernel/get-deps
[ovmf-bins]: https://github.com/osdev0/edk2-ovmf-stable-bins/releases
[qemu-rv]: https://www.qemu.org/docs/master/system/riscv/virt.html
[qemu-arm]: https://github.com/qemu/qemu/blob/v11.1.2/docs/system/arm/virt.rst
[qemu-x86]: https://github.com/qemu/qemu/blob/v11.1.2/docs/system/target-i386-desc.rst.inc
[qemu-edk2]: https://github.com/qemu/qemu/commit/065e2ecf79
[hb-qemu]: https://formulae.brew.sh/formula/qemu
[hb-limine]: https://formulae.brew.sh/formula/limine
[hb-limine-rb]: https://github.com/Homebrew/homebrew-core/blob/36dcbfff1896bc9f9195a2a0a94e30b75639f65c/Formula/l/limine.rb
[hb-xorriso]: https://formulae.brew.sh/formula/xorriso
[hb-mtools]: https://formulae.brew.sh/formula/mtools
[hb-gpt]: https://formulae.brew.sh/formula/gptfdisk
[hb-llvm]: https://formulae.brew.sh/formula/llvm
[u-n-x86]: https://packages.ubuntu.com/noble/qemu-system-x86
[u-n-arm]: https://packages.ubuntu.com/noble/qemu-system-arm
[u-n-misc]: https://packages.ubuntu.com/noble/amd64/qemu-system-misc/filelist
[u-n-data]: https://packages.ubuntu.com/noble/all/qemu-system-data/filelist
[u-n-ovmf]: https://packages.ubuntu.com/noble/ovmf
[u-n-ovmf-f]: https://packages.ubuntu.com/noble/all/ovmf/filelist
[u-n-aa]: https://packages.ubuntu.com/noble/qemu-efi-aarch64
[u-n-aa-f]: https://packages.ubuntu.com/noble/all/qemu-efi-aarch64/filelist
[u-n-rv]: https://packages.ubuntu.com/noble/qemu-efi-riscv64
[u-n-rv-f]: https://packages.ubuntu.com/noble/all/qemu-efi-riscv64/filelist
[u-n-xor]: https://packages.ubuntu.com/noble/xorriso
[u-n-mt]: https://packages.ubuntu.com/noble/mtools
[u-n-gd]: https://packages.ubuntu.com/noble/gdisk
[u-n-lim]: https://packages.ubuntu.com/noble/limine
[u-r-x86]: https://packages.ubuntu.com/resolute/qemu-system-x86
[u-r-arm]: https://packages.ubuntu.com/resolute/qemu-system-arm
[u-r-rv]: https://packages.ubuntu.com/resolute/qemu-system-riscv
[u-r-ovmf]: https://packages.ubuntu.com/resolute/ovmf
[u-r-ovmfg-f]: https://packages.ubuntu.com/resolute/all/ovmf-generic/filelist
[u-r-aa]: https://packages.ubuntu.com/resolute/qemu-efi-aarch64
[u-r-rvefi]: https://packages.ubuntu.com/resolute/qemu-efi-riscv64
[u-r-xor]: https://packages.ubuntu.com/resolute/xorriso
[u-r-mt]: https://packages.ubuntu.com/resolute/mtools
[u-r-gd]: https://packages.ubuntu.com/resolute/gdisk
[u-r-lim]: https://packages.ubuntu.com/resolute/limine
[gha]: https://github.com/actions/runner-images#available-images
[gha-2404]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md

