# Nova's build. See docs/building.md for the prerequisites and the targets.

# GNU Make 4.3 or newer. This check comes first and uses only syntax that Make 3.81, which is what
# macOS ships as /usr/bin/make, can parse, so that it can say what is wrong.
nova_make_major := $(word 1,$(subst ., ,$(MAKE_VERSION)))
nova_make_minor := $(word 2,$(subst ., ,$(MAKE_VERSION)))
ifeq ($(filter-out 0 1 2 3,$(nova_make_major)),)
nova_make_old := yes
else ifeq ($(nova_make_major),4)
ifeq ($(filter-out 0 1 2,$(nova_make_minor)),)
nova_make_old := yes
endif
endif
ifdef nova_make_old
$(error GNU Make 4.3 or newer is required, but this is GNU Make $(MAKE_VERSION). On macOS install Homebrew's make and run gmake instead of make. On Linux install a newer GNU Make)
endif

.SUFFIXES:
.DELETE_ON_ERROR:
MAKEFLAGS += --no-builtin-rules

# Per-machine overrides, which git ignores. See config.mk.example.
-include config.mk

.DEFAULT_GOAL := all

include mk/tools.mk
include mk/kernel.mk
include mk/check.mk
include mk/lint.mk

.PHONY: all
all: kernel

.PHONY: clean
clean:
	$(Q)rm -rf '$(BUILD_DIR)/$(ARCH)'

# distclean removes the whole build directory, so it only does that to one that Nova made.
.PHONY: distclean
distclean:
	$(Q)if [ -e '$(BUILD_DIR)' ] && [ ! -f '$(BUILD_DIR)/.nova-build' ]; then \
	    echo "$(BUILD_DIR) is not a Nova build directory, so it was not removed" >&2; exit 1; fi
	$(Q)rm -rf '$(BUILD_DIR)'

.PHONY: help
help:
	@echo 'Targets:'
	@echo '  kernel     build the kernel (the default target for now)'
	@echo '  check      build the kernel, then run the fixtures'
	@echo '  lint       check formatting, run clang-tidy and ruff (CI runs this as its own job)'
	@echo '  format     rewrite C and Python in place to the style that lint checks'
	@echo '  clean      remove the build output for ARCH'
	@echo '  distclean  remove the whole build directory'
	@echo 'Variables:'
	@echo '  ARCH=      the port to build, x86_64 (the default) is the only one'
	@echo '  OPT=       optimisation and debug flags, -O2 -g by default'
	@echo '  WERROR=    -Werror by default, empty to turn warnings back into warnings'
	@echo '  V=1        print each command in full'
	@echo '  BUILD_DIR= where output goes, build by default'
	@echo 'Per-machine settings (CC, LD, OBJCOPY, NM, PYTHON) go in config.mk, and so do'
	@echo 'CLANG_FORMAT, CLANG_TIDY and RUFF, which lint and format run.'
