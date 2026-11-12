# Formatting, static analysis and the compile database that clang-tidy reads.
#
#   make lint    clang-format --dry-run, clang-tidy, ruff check and ruff format --check, each on a
#                file at a time, so that a second run only redoes what changed
#   make format  rewrites C and Python in place
#
# CI runs make lint as its own job, with the tool versions in mk/versions.env. Locally this runs
# whatever is installed, and warns when a version differs.

include mk/versions.env

# Found on PATH, which includes Homebrew's llvm directory on macOS.
CLANG_FORMAT ?= clang-format
CLANG_TIDY ?= clang-tidy
RUFF ?= ruff

# Each of these stops with one message when a tool is missing, and warns when one isn't the pin.
nova_check_tools = $(PYTHON) tools/check_lint_tools.py --llvm '$(LLVM_VERSION)' \
    --ruff-version '$(RUFF_VERSION)' --clang-format '$(CLANG_FORMAT)' --ruff '$(RUFF)'

.PHONY: lint format lint-tools format-tools
lint-tools:
	$(Q)$(nova_check_tools) --clang-tidy '$(CLANG_TIDY)'
format-tools:
	$(Q)$(nova_check_tools)

# The compile database: every C source that the build compiles, with the command that compiles it,
# written from the same variables the build's rules use. clang-tidy reads it, and so does a
# committed .clangd for editors. A build that compiles C registers it by adding a name to
# NOVA_COMPDB, with its command in <name>.compdb and its sources in <name>.srcs. A subsystem
# does, in mk/kernel.mk, and userland and the host tests do the same. Names must be unique.
ifneq ($(nova_build_goals),)

COMPDB := $(BUILD)/compile_commands.json

# FORCE runs this every time, and the tool leaves the file alone unless its contents differ, so
# that adding or removing a source or changing a flag is noticed and nothing else is.
$(COMPDB): FORCE
	$(Q)$(PYTHON) tools/compile_db.py --directory '$(CURDIR)' --output $@ \
	    $(foreach g,$(NOVA_COMPDB),--group '$($(g).compdb)' '$(filter %.c,$($(g).srcs))')

# Every build writes it, so that an editor has it after one.
kernel: $(COMPDB)

endif

ifneq ($(filter lint format,$(nova_goals)),)

# Nova's own code. third_party/ is never linted, wherever it is, which includes the vendored code
# that a fixture carries.
nova_lint_dirs := $(wildcard kernel user tests tools mk)
nova_lint_files := $(shell find $(nova_lint_dirs) -type f -not -path '*/third_party/*' | sort)
nova_c_files := $(filter %.c %.h,$(nova_lint_files))
nova_py_files := $(filter %.py,$(nova_lint_files))

format: format-tools
	$(call nova_say,FORMAT,$(words $(nova_c_files)) C files)
	$(Q)$(CLANG_FORMAT) -i $(nova_c_files)
	$(call nova_say,FORMAT,$(words $(nova_py_files)) Python files)
	$(Q)$(RUFF) format --no-cache --quiet $(nova_py_files)

endif

ifneq ($(filter lint,$(nova_goals)),)

LINT := $(BUILD)/lint

# A file is checked again when it changes, and so is every file that clang-tidy analyses when what
# it reads changes: a header (which the sources may include), the configuration, the compile
# database or the shim of freestanding headers. The prelude is a header too.
nova_tidy_files := $(foreach g,$(NOVA_COMPDB),$(filter %.c,$($(g).srcs)))
nova_tidy_inputs := .clang-tidy $(filter %/.clang-tidy,$(nova_lint_files)) \
    $(filter %.h,$(nova_lint_files)) $(COMPDB) $(SHIM)/.stamp

nova_format_stamps := $(addprefix $(LINT)/,$(addsuffix .format.ok,$(nova_c_files)))
nova_tidy_stamps := $(addprefix $(LINT)/,$(addsuffix .tidy.ok,$(nova_tidy_files)))
nova_ruff_stamps := $(addprefix $(LINT)/,$(addsuffix .ruff.ok,$(nova_py_files)))

$(nova_format_stamps): $(LINT)/%.format.ok: % .clang-format | lint-tools
	$(call nova_say,FORMAT,$<)
	$(Q)$(CLANG_FORMAT) --dry-run --Werror $<
	$(Q)mkdir -p $(@D) && touch $@

$(nova_tidy_stamps): $(LINT)/%.tidy.ok: % $(nova_tidy_inputs) | lint-tools
	$(call nova_say,TIDY,$<)
	$(Q)$(CLANG_TIDY) --quiet -p $(BUILD) $<
	$(Q)mkdir -p $(@D) && touch $@

$(nova_ruff_stamps): $(LINT)/%.ruff.ok: % ruff.toml | lint-tools
	$(call nova_say,RUFF,$<)
	$(Q)$(RUFF) check --no-cache --quiet $<
	$(Q)$(RUFF) format --no-cache --quiet --check $<
	$(Q)mkdir -p $(@D) && touch $@

lint: lint-tools $(nova_format_stamps) $(nova_ruff_stamps) $(nova_tidy_stamps)

endif
