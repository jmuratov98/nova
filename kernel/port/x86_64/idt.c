#include <stdint.h>

#include "x86.h"
#include <port/cpu.h>

/*
 * The IDT: an interrupt gate for every one of the 256 vectors, each pointing at its stub in
 * vectors.S, so that from the moment it loads no vector can find an empty gate and triple-fault.
 * Interrupt gates mask interrupts on entry. #DF, NMI and #MC switch to stacks of their own (gdt.c).
 */

#define VECTOR_NMI 2
#define VECTOR_DOUBLE_FAULT 8
#define VECTOR_MACHINE_CHECK 18

#define GATE_INTERRUPT 0x8e /* present, ring 0, a 64-bit interrupt gate */

struct gate {
    uint16_t offset_low;
    uint16_t selector;
    uint8_t ist;
    uint8_t type;
    uint16_t offset_middle;
    uint32_t offset_high;
    uint32_t reserved;
};

_Static_assert(sizeof(struct gate) == 16, "an IDT gate is 16 bytes");

static struct gate idt[VECTOR_COUNT] __attribute__((aligned(16)));

static uint8_t ist_of(unsigned vector) {
    switch (vector) {
    case VECTOR_DOUBLE_FAULT:
        return IST_DOUBLE_FAULT;
    case VECTOR_NMI:
        return IST_NMI;
    case VECTOR_MACHINE_CHECK:
        return IST_MACHINE_CHECK;
    default:
        return 0;
    }
}

void idt_load(void) {
    for (unsigned vector = 0; vector < VECTOR_COUNT; vector++) {
        uint64_t stub = (uintptr_t)port_vectors + (uint64_t)vector * VECTOR_STUB_SIZE;
        idt[vector] = (struct gate){
            .offset_low = (uint16_t)stub,
            .selector = KERNEL_CODE_SELECTOR,
            .ist = ist_of(vector),
            .type = GATE_INTERRUPT,
            .offset_middle = (uint16_t)(stub >> 16U),
            .offset_high = (uint32_t)(stub >> 32U),
            .reserved = 0,
        };
    }

    struct descriptor_pointer pointer = {sizeof(idt) - 1, (uintptr_t)idt};
    __asm__ volatile("lidt %0" : : "m"(pointer));
}

noreturn void port_trap(void) { port_power_off(PORT_OUTCOME_PANIC); }
