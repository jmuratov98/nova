# make check: everything that needs no QEMU, boot image or network. For now that is the fixtures.

.PHONY: check
check: kernel
	$(Q)$(PYTHON) tools/run_fixtures.py --make '$(MAKE)' -- \
	    'ARCH=$(ARCH)' 'PYTHON=$(PYTHON)' 'CC=$(CC)' 'LD=$(LD)' 'OBJCOPY=$(OBJCOPY)' 'NM=$(NM)' \
	    'OPT=$(OPT)' 'WERROR=$(WERROR)'
