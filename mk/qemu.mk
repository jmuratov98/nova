# Running and debugging Nova in QEMU, on the one machine that the port defines (PORT_QEMU_MACHINE
# in its port.mk). These add only display, serial and gdbstub flags to it.
#
#   make run     boot it, with a window, and serial plus QEMU's monitor in this terminal
#                (Ctrl-A C switches between them, Ctrl-A X quits)
#   make debug   the same, paused at the first instruction, with a gdbstub on 127.0.0.1
#   make lldb    in a second terminal: load the kernel's symbols, connect to `make debug`, stop at
#                kmain
#
# A run ends when the kernel powers off with an outcome, and one line says which (ADR 0006). The
# target succeeds only when init exited 0, so make doesn't report QEMU's exit status as an error.

QEMU ?= $(PORT_QEMU)
LLDB ?= lldb
FIRMWARE ?= $(firstword $(PORT_FIRMWARES))
DEBUG_PORT ?= 1234
QEMUFLAGS ?=

FIRMWARE_DIR := $(CACHE)/qemu-$(PORT_FIRMWARE_TAG)
QEMU_STATE := $(BUILD)/qemu

ifneq ($(filter run debug,$(nova_goals)),)
ifeq ($(filter $(FIRMWARE),$(PORT_FIRMWARES)),)
$(error FIRMWARE=$(FIRMWARE) is not supported. The $(ARCH) port boots under: $(PORT_FIRMWARES))
endif
endif

# One rule per firmware download, from the port's name=sha256 list. A .bz2 is unpacked on the way
# in, under its name without .bz2.
define nova_firmware_download
$(FIRMWARE_DIR)/$(patsubst %.bz2,%,$(1)):
	$$(call nova_say,FETCH,$(PORT_FIRMWARE_URL)/$(1))
	$$(Q)$$(PYTHON) tools/fetch.py --url '$(PORT_FIRMWARE_URL)/$(1)' --sha256 $(2) \
	    $(if $(filter %.bz2,$(1)),--bunzip2) --output $$@
endef
$(foreach d,$(PORT_FIRMWARE_DOWNLOADS),$(eval $(call nova_firmware_download,$(firstword \
    $(subst =, ,$(d))),$(lastword $(subst =, ,$(d))))))

nova_firmware_files := $(addprefix $(FIRMWARE_DIR)/,$(PORT_FIRMWARE_FILES.$(FIRMWARE)))

# Before every launch: a fresh directory for QEMU's writable state, and whatever the firmware needs
# there, such as a fresh copy of UEFI's variables.
nova_qemu_prepare = mkdir -p $(QEMU_STATE)$(if $(PORT_QEMU_PREPARE.$(FIRMWARE)), && \
    $(PORT_QEMU_PREPARE.$(FIRMWARE)))

nova_qemu = $(PYTHON) tools/run_qemu.py --qemu '$(QEMU)' --outcomes '$(PORT_QEMU_OUTCOMES)' -- \
    $(PORT_QEMU_MACHINE) $(PORT_QEMU_FIRMWARE.$(FIRMWARE))

.PHONY: run debug lldb
run: $(IMAGE) $(nova_firmware_files)
	$(Q)$(nova_qemu_prepare)
	$(Q)$(nova_qemu) -serial mon:stdio $(QEMUFLAGS)

debug: $(IMAGE) $(nova_firmware_files)
	$(Q)$(nova_qemu_prepare)
	@echo 'QEMU is paused, with a gdbstub on 127.0.0.1:$(DEBUG_PORT). Run `make lldb` in another terminal.'
	$(Q)$(nova_qemu) -serial mon:stdio -S -gdb tcp:127.0.0.1:$(DEBUG_PORT) $(QEMUFLAGS)

# lldb is the supported debugger. tools/lldb/nova.lldb holds what to do once connected.
lldb: $(KERNEL)
	$(Q)$(call nova_need,$(LLDB),debug the kernel)
	$(Q)$(LLDB) $(KERNEL) -o 'gdb-remote 127.0.0.1:$(DEBUG_PORT)' -s tools/lldb/nova.lldb
