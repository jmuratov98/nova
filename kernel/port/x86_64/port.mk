# The x86-64 port's makefile fragment. The top-level Makefile includes the one for $(ARCH), so
# adding a port means adding a directory with a fragment like this one.

# What clang targets, and the codegen flags that this architecture's kernel needs.
PORT_TRIPLE := x86_64-unknown-none-elf
PORT_CFLAGS := -mcmodel=kernel -mno-red-zone -mgeneral-regs-only

# The linker script, the symbol that it names as the kernel's entry point, and the ELF machine
# number that the image must have (EM_X86_64).
PORT_LDSCRIPT := kernel/port/x86_64/kernel.ld
PORT_ENTRY := port_entry
PORT_ELF_MACHINE := 62
