/*
 * The stubs that the IDT points at, one for each of the 256 vectors, VECTOR_STUB_SIZE bytes apart
 * from port_vectors (idt.c relies on the stride). Each pushes 0 where the CPU pushes no error code,
 * so that every frame has the same shape, then its vector number.
 *
 * Nothing handles an interrupt or an exception yet, so every stub goes to port_trap, which ends the
 * run with the panic outcome. The frame is left where it is.
 */

#include "x86.h"

/*
 * The CPU pushes an error code for #DF, #TS, #NP, #SS, #GP, #PF, #AC, #CP, #VC and #SX. .org puts
 * each stub at its slot, and fails to assemble if the stub before it grew past its own.
 */
.macro vector n
    .org port_vectors + (\n) * VECTOR_STUB_SIZE, 0xcc
    .if ((\n) == 8) || (((\n) >= 10) && ((\n) <= 14)) || ((\n) == 17) || ((\n) == 21) || ((\n) == 29) || ((\n) == 30)
    .else
    pushq $0
    .endif
    pushq $(\n)
    jmp vector_common
.endm

    .text
    .balign VECTOR_STUB_SIZE
NOVA_FUNC port_vectors
    .irp high, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    .irp low, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    vector (\high * 16 + \low)
    .endr
    .endr
    .org port_vectors + VECTOR_COUNT * VECTOR_STUB_SIZE, 0xcc
NOVA_END port_vectors

/*
 * The stubs' common path. The CPU pushed five words and the stub two, which leaves the stack 8
 * bytes off the 16-byte alignment that a call needs.
 */
vector_common:
    cld
    andq $-16, %rsp
    call port_trap
    ud2

/*
 * Where SYSCALL lands, through LSTAR (cpu.c). Nothing makes a system call yet, so one ends the run
 * the same way.
 */
NOVA_FUNC port_syscall_entry
    andq $-16, %rsp
    call port_trap
    ud2
NOVA_END port_syscall_entry
