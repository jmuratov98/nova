# The x86-64 port's makefile fragment. The top-level Makefile includes the one for $(ARCH), so
# adding a port means adding a directory with a fragment like this one. It only sets variables,
# and the rules in mk/ use them.

# What clang targets, and the codegen flags that this architecture's kernel needs.
PORT_TRIPLE := x86_64-unknown-none-elf
PORT_CFLAGS := -mcmodel=kernel -mno-red-zone -mgeneral-regs-only

# The linker script, the symbol that it names as the kernel's entry point, and the ELF machine
# number that the image must have (EM_X86_64).
PORT_LDSCRIPT := kernel/port/x86_64/kernel.ld
PORT_ENTRY := port_entry
PORT_ELF_MACHINE := 62

# The boot image: one hybrid ISO that boots under both BIOS and UEFI. xorriso writes it with
# Limine's El Torito images for both, and `limine bios-install` then makes it bootable from a
# BIOS. mk/image.mk runs this as the recipe for $(IMAGE), with the Limine release unpacked in
# $(LIMINE_DIR) and its command-line tool built at $(LIMINE_TOOL). xorriso is chatty, so what it
# says is shown only when it fails.
PORT_IMAGE := nova.iso
define PORT_IMAGE_RECIPE
$(Q)rm -rf $@.root $@.tmp
$(Q)mkdir -p $@.root/boot/limine $@.root/EFI/BOOT
$(Q)cp $(KERNEL) $@.root/boot/kernel
$(Q)cp mk/limine.conf $(LIMINE_DIR)/limine-bios.sys $(LIMINE_DIR)/limine-bios-cd.bin \
    $(LIMINE_DIR)/limine-uefi-cd.bin $@.root/boot/limine/
$(Q)cp $(LIMINE_DIR)/BOOTX64.EFI $@.root/EFI/BOOT/
$(Q)log=$$($(XORRISO) -as mkisofs -R -r -J \
    -b boot/limine/limine-bios-cd.bin -no-emul-boot -boot-load-size 4 -boot-info-table \
    -hfsplus -apm-block-size 2048 \
    --efi-boot boot/limine/limine-uefi-cd.bin -efi-boot-part --efi-boot-image \
    --protective-msdos-label $@.root -o $@.tmp 2>&1) || { printf '%s\n' "$$log" >&2; exit 1; }
$(Q)$(LIMINE_TOOL) bios-install --quiet $@.tmp
$(Q)rm -rf $@.root
$(Q)mv $@.tmp $@
endef

# The QEMU machine, defined once. `make run` and `make debug` (mk/qemu.mk) add only display,
# serial and gdbstub flags to it, so they boot exactly the machine that the boot test boots.
# isa-debug-exit is how the kernel hands QEMU its outcome (ADR 0006).
PORT_QEMU := qemu-system-x86_64
PORT_QEMU_MACHINE = -machine q35 -accel tcg -cpu qemu64,+smep,+smap -smp 1 -m 256M \
    -nic none -no-reboot -device isa-debug-exit,iobase=0xf4,iosize=0x04 \
    -cdrom $(IMAGE) -boot d

# QEMU's exit status for each outcome, in the order init exited 0, init exited non-zero, panic.
# isa-debug-exit exits with (v << 1) | 1, and the port writes 0x10, 0x11 or 0x12.
PORT_QEMU_OUTCOMES := 33 35 37

# Firmware, from QEMU's own pc-bios/ at a pinned tag, each download checked against its sha256.
# These are byte for byte what Homebrew's QEMU ships. The edk2 images are bz2 there, and are
# unpacked on the way into the cache.
PORT_FIRMWARE_TAG := v11.1.0
PORT_FIRMWARE_URL := https://gitlab.com/qemu-project/qemu/-/raw/$(PORT_FIRMWARE_TAG)/pc-bios
PORT_FIRMWARE_DOWNLOADS := \
    bios-256k.bin=ae6f6aa973aaccc143f57aa960fb035fd9de4daee4ad0cd713322f8c259e7650 \
    edk2-x86_64-code.fd.bz2=f4d7c29fccb5e1d4d851eaddc41a5c4feec7de96ca7ad9bbf96f4d09838ef973 \
    edk2-i386-vars.fd.bz2=83470f393b9a200838b2292a65ca5708a109005d65a6422f3fa23cb21c8179b9

# The firmwares that FIRMWARE= may name, the first being the default. For each: the files it
# needs from the cache ($(FIRMWARE_DIR)), its QEMU flags, and what to do before every launch.
# UEFI's code is read-only, and its variables are a fresh copy of the template each time, so no
# boot state carries over from one run to the next. -bios can't load either 4 MiB image.
PORT_FIRMWARES := uefi bios
PORT_FIRMWARE_FILES.uefi := edk2-x86_64-code.fd edk2-i386-vars.fd
PORT_QEMU_FIRMWARE.uefi = \
    -drive if=pflash,unit=0,format=raw,readonly=on,file=$(FIRMWARE_DIR)/edk2-x86_64-code.fd \
    -drive if=pflash,unit=1,format=raw,file=$(QEMU_STATE)/uefi-vars.fd
PORT_QEMU_PREPARE.uefi = cp $(FIRMWARE_DIR)/edk2-i386-vars.fd $(QEMU_STATE)/uefi-vars.fd
PORT_FIRMWARE_FILES.bios := bios-256k.bin
PORT_QEMU_FIRMWARE.bios = -bios $(FIRMWARE_DIR)/bios-256k.bin
PORT_QEMU_PREPARE.bios =
