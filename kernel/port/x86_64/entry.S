/*
 * The kernel's entry point, a placeholder that halts. The linker script names it with ENTRY, so it
 * is exported. Nothing calls into the portable kernel yet.
 */

    .text

NOVA_EXPORT_FUNC port_entry
    call port_irq_disable
1:
    hlt
    jmp 1b
NOVA_END port_entry
