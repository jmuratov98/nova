# The prerequisites on macOS: run `brew bundle`. See docs/building.md.

# GNU Make 4.3 or newer. macOS's own make is 3.81, so run it as gmake.
brew "make"

# Python 3.11 or newer, which is newer than the python3 that macOS ships. The build uses only the
# standard library.
brew "python"

# llvm-objcopy and llvm-nm, and a clang if you'd rather not use Apple's. This is keg-only, but the
# build looks in its directory without it being on PATH.
brew "llvm"

# ld.lld
brew "lld"

# What `make lint` and `make format` run. clang-format and clang-tidy come with llvm above, and
# ruff checks and formats the Python.
brew "ruff"
