/*
 * The x86-64 kernel image: three page-aligned segments (read, read and execute, read and write)
 * in the top 2 GiB of the address space, as -mcmodel=kernel requires.
 */

ENTRY(port_entry)

PHDRS {
    rodata PT_LOAD FLAGS(4);
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

SECTIONS {
    . = 0xffffffff80000000;

    . = ALIGN(4096);
    .rodata : {
        *(.rodata .rodata.*)
    } :rodata

    . = ALIGN(4096);
    .text : {
        *(.text .text.*)
    } :text

    . = ALIGN(4096);
    .data : {
        *(.data .data.*)
    } :data

    .bss : {
        *(.bss .bss.*)
        *(COMMON)
    } :data

    /DISCARD/ : {
        *(.eh_frame .eh_frame_hdr)
        *(.comment)
        *(.note.GNU-stack)
    }
}
