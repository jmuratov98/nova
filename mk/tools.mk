# The port and the toolchain, which ADR 0005 fixes: any clang, and LLVM's ld.lld, llvm-objcopy and
# llvm-nm. GCC and GNU binutils aren't supported.

# ARCH selects a port. A port is a directory under kernel/port/ with a makefile fragment, so these
# are the architectures that exist, and today that is x86_64 only.
ARCH ?= x86_64
nova_ports := $(patsubst kernel/port/%/port.mk,%,$(wildcard kernel/port/*/port.mk))
ifeq ($(filter $(ARCH),$(nova_ports)),)
$(error ARCH=$(ARCH) is not supported. The available ports are: $(nova_ports))
endif

PYTHON ?= python3

# Make has its own defaults for some of these (cc and ld), which aren't what we want. Anything set
# in config.mk, in the environment or on the command line wins.
nova_default = $(if $(filter default undefined,$(origin $(1))),$(eval $(1) := $(2)))
$(call nova_default,CC,clang)
$(call nova_default,LD,ld.lld)
$(call nova_default,OBJCOPY,llvm-objcopy)
$(call nova_default,NM,llvm-nm)

# Homebrew's llvm is keg-only on macOS. These come last, so that a clang already on PATH (Apple's)
# still wins.
export PATH := $(PATH):/opt/homebrew/opt/llvm/bin:/usr/local/opt/llvm/bin

# One configuration, -O2 -g, that OPT replaces. -Werror applies to everything that Nova compiles,
# and an empty WERROR turns it off, for a local clang that is newer than CI's.
OPT ?= -O2 -g
WERROR ?= -Werror

# The one warning set, shared by the kernel, userland and the host tests.
nova_warnings := -Wall -Wextra -Wpedantic \
    -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wmissing-variable-declarations \
    -Wcast-qual -Wundef -Wvla -Wformat=2 -Wpointer-arith -Wwrite-strings -Wimplicit-fallthrough

# V=1 prints every command in full. Otherwise each step prints one short line.
ifeq ($(V),1)
Q :=
nova_say =
else
Q := @
nova_say = @printf '  %-6s %s\n' '$(1)' '$(2)'
endif
