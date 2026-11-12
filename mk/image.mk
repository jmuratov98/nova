# The boot image: the kernel and Limine, put together by the port's recipe (PORT_IMAGE_RECIPE in
# its port.mk).
#
# Limine is a release downloaded at a pinned tag and checked against the sha256 below. Like the
# firmware, it goes into the cache, $(CACHE), which `make clean` keeps and `make distclean`
# removes, so only the first image build needs the network. Compiling never does: limine.h is
# vendored in third_party/limine/. The release's `limine` tool, which installs the BIOS boot code,
# is built from its limine.c with the host compiler.

# The release, and the sha256 of its limine-binary.tar.gz. Releases are immutable, and this one's
# GPG signature was checked against Limine's signing key when it was pinned. limine.h comes from
# the protocol commit that this release pins (third_party/limine/README.md).
LIMINE_VERSION := 12.9.6
LIMINE_SHA256 := b38aabb042b0c0f9f562b7741be3c1204838d7bbacfa78bb411c674bd5b984ee
LIMINE_URL := https://github.com/Limine-Bootloader/Limine/releases/download/v$(LIMINE_VERSION)/limine-binary.tar.gz

CACHE := $(BUILD_DIR)/cache
LIMINE_TARBALL := $(CACHE)/limine-$(LIMINE_VERSION)-binary.tar.gz
LIMINE_DIR := $(CACHE)/limine-$(LIMINE_VERSION)
LIMINE_TOOL := $(BUILD)/limine/limine
IMAGE := $(BUILD)/$(PORT_IMAGE)

# The host compiler, for tools that run on the build machine. xorriso writes the image.
HOSTCC ?= cc
XORRISO ?= xorriso

# Stops with one message when a program that a target needs isn't installed. $(1) is the command,
# which may carry arguments, as in LLDB='lldb --batch'. The reason, $(2), goes in double quotes.
nova_need = command -v '$(firstword $(1))' > /dev/null 2>&1 || \
    { echo "$(firstword $(1)) is needed to $(2), but it was not found. See docs/building.md" >&2; \
    exit 1; }

$(LIMINE_TARBALL):
	$(call nova_say,FETCH,$(LIMINE_URL))
	$(Q)$(PYTHON) tools/fetch.py --url '$(LIMINE_URL)' --sha256 $(LIMINE_SHA256) --output $@

$(LIMINE_DIR)/.unpacked: $(LIMINE_TARBALL)
	$(Q)rm -rf $(@D) && mkdir -p $(@D)
	$(Q)tar -xzf $< -C $(@D) --strip-components=1
	$(Q)touch $@

$(LIMINE_TOOL): $(LIMINE_DIR)/.unpacked
	$(call nova_say,HOSTCC,$@)
	$(Q)$(call nova_need,$(HOSTCC),build the limine tool for the boot image)
	$(Q)mkdir -p $(@D)
	$(Q)$(HOSTCC) -O2 -std=c99 -D_FILE_OFFSET_BITS=64 -o $@ $(LIMINE_DIR)/limine.c

$(IMAGE): $(KERNEL) mk/limine.conf $(LIMINE_DIR)/.unpacked $(LIMINE_TOOL) mk/image.mk \
    kernel/port/$(ARCH)/port.mk
	$(call nova_say,IMAGE,$@)
	$(Q)$(call nova_need,$(XORRISO),build the boot image)
	$(PORT_IMAGE_RECIPE)

.PHONY: image
image: $(IMAGE)
