# Building the kernel: each subsystem is compiled, partially linked into one relocatable object
# and made to hide what it doesn't export (ADR 0003), and the objects are linked into the image.

include kernel/port/$(ARCH)/port.mk

# Output goes out of tree, in one directory per port.
BUILD_DIR ?= build
BUILD := $(BUILD_DIR)/$(ARCH)
OBJ := $(BUILD)/obj
SUB := $(BUILD)/sub
SHIM := $(BUILD)/shim
KERNEL := $(BUILD)/kernel.elf

# Freestanding C17 with nothing hosted visible, and trapping UBSan, which needs no runtime library.
# NOVA_EXPORT and the assembly macros come from the prelude.
KERNEL_CFLAGS := --target=$(PORT_TRIPLE) -std=c17 -ffreestanding -nostdinc -isystem $(SHIM) \
    $(PORT_CFLAGS) -fno-pic -fno-pie -fno-stack-protector -fno-lto -fvisibility=hidden \
    -fno-common -fno-omit-frame-pointer -fsanitize=undefined -fsanitize-trap=undefined \
    $(OPT) $(nova_warnings) -Wframe-larger-than=1024 $(WERROR) -include mk/prelude.h
KERNEL_ASFLAGS := --target=$(PORT_TRIPLE) -ffreestanding -nostdinc -isystem $(SHIM) \
    -include mk/prelude.h $(OPT) $(WERROR)

# Everything below needs the toolchain, and what a clean doesn't. Neither does formatting.
nova_goals := $(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))
nova_build_goals := $(filter-out clean distclean help format,$(nova_goals))
ifneq ($(nova_build_goals),)

nova_python_ok := $(shell PATH='$(PATH)' $(PYTHON) -c 'import sys; print(sys.version_info >= (3, 11))' 2>/dev/null)
ifneq ($(nova_python_ok),True)
$(error Python 3.11 or newer is required, but '$(PYTHON)' wasn't found or is older. See docs/building.md)
endif

# Parse-time steps print nothing when they succeed, and their message when they don't.
nova_run = $(shell PATH='$(PATH)' $(PYTHON) $(1) 2>&1)

nova_problem := $(call nova_run,tools/check_env.py --cc '$(CC)' --ld '$(LD)' --objcopy '$(OBJCOPY)' --nm '$(NM)' -- $(KERNEL_CFLAGS))
ifneq ($(nova_problem),)
$(error $(nova_problem))
endif

nova_init := $(shell mkdir -p '$(BUILD)' && touch '$(BUILD_DIR)/.nova-build')

nova_problem := $(call nova_run,tools/subsystems.py makefile --arch $(ARCH) --output $(BUILD)/subsystems.mk)
ifneq ($(nova_problem),)
$(error $(nova_problem))
endif
include $(BUILD)/subsystems.mk

# Anything that changes what the compiler would produce is in the stamp, so changing it rebuilds
# everything. FORCE only rewrites the stamp when its contents differ.
nova_cc_id := $(shell PATH='$(PATH)' $(CC) --version 2>&1 | head -n 1)
nova_config := $(nova_cc_id) $(foreach t,$(NOVA_TOOLS),$($(t))) $(KERNEL_CFLAGS) $(KERNEL_ASFLAGS) \
    $(foreach s,$(SUBSYSTEMS),$(s): $($(s).includes))
CONFIG_STAMP := $(BUILD)/config.stamp
$(CONFIG_STAMP): FORCE
	$(Q)printf '%s\n' '$(nova_config)' | cmp -s - $@ || printf '%s\n' '$(nova_config)' > $@

$(SHIM)/.stamp: tools/make_shim.py $(CONFIG_STAMP)
	$(call nova_say,SHIM,$(SHIM))
	$(Q)$(PYTHON) tools/make_shim.py --cc '$(CC)' --output $(SHIM)
	$(Q)touch $@

# The source checks run before anything is compiled, so that a rule they enforce is reported as
# that rule and not as whatever the compiler makes of it. Objects only wait for them, because a
# change that passes the checks isn't a reason to compile again.
SOURCES_OK := $(BUILD)/sources.ok
$(SOURCES_OK): $(SUBSYSTEM_FILES) tools/check_sources.py tools/subsystems.py
	$(call nova_say,CHECK,sources)
	$(Q)$(PYTHON) tools/check_sources.py --arch $(ARCH)
	$(Q)touch $@

nova_inputs := $(CONFIG_STAMP) $(SHIM)/.stamp mk/prelude.h

# Compiles a subsystem's sources, then partially links them into one relocatable object and makes
# every symbol that it doesn't export local to it.
define nova_subsystem
$(1).objs := $$(patsubst $$($(1).dir)/%,$(OBJ)/$(1)/%.o,$$($(1).srcs))

# The compile database (mk/lint.mk) lists this subsystem's C sources with the command below, which
# is the one the rule below compiles them with.
NOVA_COMPDB += $(1)
$(1).compdb := $(CC) $(KERNEL_CFLAGS) $$($(1).includes)

$(OBJ)/$(1)/%.c.o: $$($(1).dir)/%.c $(nova_inputs) | $(SOURCES_OK)
	$$(call nova_say,CC,$$<)
	$$(Q)mkdir -p $$(@D)
	$$(Q)$(CC) $(KERNEL_CFLAGS) $$($(1).includes) -MMD -MP -c -o $$@ $$<

$(OBJ)/$(1)/%.S.o: $$($(1).dir)/%.S $(nova_inputs) | $(SOURCES_OK)
	$$(call nova_say,AS,$$<)
	$$(Q)mkdir -p $$(@D)
	$$(Q)$(CC) $(KERNEL_ASFLAGS) $$($(1).includes) -MMD -MP -c -o $$@ $$<

$(SUB)/$(1).o: $$($(1).objs)
	$$(call nova_say,LD,$$@)
	$$(Q)mkdir -p $$(@D)
	$$(Q)$(LD) -r -o $$@.unlocalized $$^
	$$(Q)$(OBJCOPY) --localize-hidden $$@.unlocalized $$@
	$$(Q)rm -f $$@.unlocalized
endef
$(foreach s,$(SUBSYSTEMS),$(eval $(call nova_subsystem,$(s))))

SUBSYSTEM_OBJS := $(foreach s,$(SUBSYSTEMS),$(SUB)/$(s).o)

# Every header that the compiler opened, however the include was spelled, must be one that the
# subsystem may include. This runs before the symbol check, which would otherwise report what a
# forbidden header lets a subsystem reach as that.
HEADERS_OK := $(BUILD)/headers.ok
$(HEADERS_OK): $(SUBSYSTEM_OBJS) kernel/subsystems.toml tools/check_headers.py tools/subsystems.py
	$(call nova_say,CHECK,headers)
	$(Q)$(PYTHON) tools/check_headers.py --arch $(ARCH) --build-dir $(BUILD) --allow mk/prelude.h
	$(Q)touch $@

# Every undefined symbol in a subsystem's object must be one that a declared dependency exports.
SYMBOLS_OK := $(BUILD)/symbols.ok
$(SYMBOLS_OK): $(SUBSYSTEM_OBJS) kernel/subsystems.toml tools/check_symbols.py tools/subsystems.py \
    | $(HEADERS_OK)
	$(call nova_say,CHECK,symbols)
	$(Q)$(PYTHON) tools/check_symbols.py --arch $(ARCH) --build-dir $(BUILD) --nm '$(NM)'
	$(Q)touch $@

$(KERNEL): $(SUBSYSTEM_OBJS) $(HEADERS_OK) $(SYMBOLS_OK) $(PORT_LDSCRIPT)
	$(call nova_say,LINK,$@)
	$(Q)$(LD) -static --no-pie -T $(PORT_LDSCRIPT) -o $@ $(SUBSYSTEM_OBJS)
	$(Q)$(PYTHON) tools/check_kernel.py --nm '$(NM)' --machine $(PORT_ELF_MACHINE) --entry $(PORT_ENTRY) $@

-include $(wildcard $(OBJ)/*/*.d)

endif

.PHONY: kernel
kernel: $(KERNEL)

.PHONY: FORCE
FORCE:
