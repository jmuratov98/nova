/*
 * The kernel's entry point. Limine jumps here with interrupts masked, on a stack in memory that the
 * kernel will reclaim. The stub moves to the boot stack, which the kernel keeps, clears the frame
 * pointer so that a backtrace stops here, and runs the port's start-up, which ends in kmain and
 * never returns. The linker script names port_entry with ENTRY, so it is exported.
 */

#define BOOT_STACK_SIZE 16384

    .text

NOVA_EXPORT_FUNC port_entry
    leaq boot_stack_top(%rip), %rsp
    xorl %ebp, %ebp
    call port_startup
    ud2
NOVA_END port_entry

    .bss
    .balign 16
boot_stack:
    .skip BOOT_STACK_SIZE
boot_stack_top:
