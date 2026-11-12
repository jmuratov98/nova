#include <stdint.h>

#include "x86.h"
#include <port/cpu.h>

/*
 * The CPU's own set-up, power-off, and interrupt masking.
 */

#define MSR_EFER 0xc0000080
#define MSR_STAR 0xc0000081
#define MSR_LSTAR 0xc0000082
#define MSR_FMASK 0xc0000084

#define EFER_SCE (1ULL << 0U)  /* SYSCALL and SYSRET */
#define EFER_NXE (1ULL << 11U) /* the no-execute bit in page tables */

#define CR0_MP (1ULL << 1U)  /* WAIT faults when TS is set */
#define CR0_EM (1ULL << 2U)  /* x87 is emulated, which it isn't */
#define CR0_TS (1ULL << 3U)  /* the FPU state belongs to another task, which it doesn't */
#define CR0_NE (1ULL << 5U)  /* x87 errors are exceptions, not IRQ 13 */
#define CR0_WP (1ULL << 16U) /* ring 0 honours read-only pages */

#define CR4_OSFXSR (1ULL << 9U)      /* FXSAVE, FXRSTOR and SSE */
#define CR4_OSXMMEXCPT (1ULL << 10U) /* SSE errors are #XM */
#define CR4_SMEP (1ULL << 20U)       /* ring 0 can't execute user pages */
#define CR4_SMAP (1ULL << 21U)       /* ring 0 can't touch user pages unless RFLAGS.AC is set */

#define CPUID_EXTENDED 0x80000000
#define CPUID_EXTENDED_FEATURES 0x80000001
#define CPUID_STRUCTURED_FEATURES 7
#define CPUID_NX (1U << 20U)   /* in leaf 0x80000001's EDX */
#define CPUID_SMEP (1U << 7U)  /* in leaf 7's EBX */
#define CPUID_SMAP (1U << 20U) /* in leaf 7's EBX */

/* What FMASK clears on SYSCALL: IF, DF, TF, and AC, so a program can't enter with SMAP open. */
#define RFLAGS_TF (1ULL << 8U)
#define RFLAGS_IF (1ULL << 9U)
#define RFLAGS_DF (1ULL << 10U)
#define RFLAGS_AC (1ULL << 18U)

/* MXCSR with every SSE exception masked, its reset value. FNINIT leaves FCW at 0x37f. */
#define MXCSR_DEFAULT 0x1f80U

/* isa-debug-exit, at the I/O port that the QEMU machine gives it (port.mk). */
#define DEBUG_EXIT_PORT 0xf4

static uint64_t read_cr0(void) {
    uint64_t value;
    __asm__ volatile("movq %%cr0, %0" : "=r"(value));
    return value;
}

static void write_cr0(uint64_t value) { __asm__ volatile("movq %0, %%cr0" : : "r"(value)); }

static uint64_t read_cr4(void) {
    uint64_t value;
    __asm__ volatile("movq %%cr4, %0" : "=r"(value));
    return value;
}

static void write_cr4(uint64_t value) { __asm__ volatile("movq %0, %%cr4" : : "r"(value)); }

/*
 * NX is required, since every page that isn't code is mapped no-execute. SMEP and SMAP are used
 * when the CPU has them. The FPU and SSE are set up for userland, which uses the full ABI, while
 * the kernel itself is built without them.
 */
void cpu_setup(void) {
    if (cpuid(CPUID_EXTENDED, 0).eax < CPUID_EXTENDED_FEATURES ||
        (cpuid(CPUID_EXTENDED_FEATURES, 0).edx & CPUID_NX) == 0) {
        port_power_off(PORT_OUTCOME_PANIC);
    }

    wrmsr(MSR_EFER, rdmsr(MSR_EFER) | EFER_SCE | EFER_NXE);
    write_cr0((read_cr0() | CR0_WP | CR0_MP | CR0_NE) & ~(CR0_EM | CR0_TS));

    uint64_t cr4 = read_cr4() | CR4_OSFXSR | CR4_OSXMMEXCPT;
    if (cpuid(0, 0).eax >= CPUID_STRUCTURED_FEATURES) {
        uint32_t features = cpuid(CPUID_STRUCTURED_FEATURES, 0).ebx;
        cr4 |= (features & CPUID_SMEP) ? CR4_SMEP : 0;
        cr4 |= (features & CPUID_SMAP) ? CR4_SMAP : 0;
    }
    write_cr4(cr4);

    uint32_t mxcsr = MXCSR_DEFAULT;
    __asm__ volatile("fninit\n\t"
                     "ldmxcsr %0"
                     :
                     : "m"(mxcsr));

    /*
     * SYSCALL loads CS from STAR[47:32] and SS from 8 more. SYSRET, which Nova doesn't use, would
     * load SS from STAR[63:48] + 8 and CS from + 16, which is why user data comes before user code.
     */
    wrmsr(MSR_STAR,
          ((uint64_t)(USER_DATA_SELECTOR - 8U) << 48U) | ((uint64_t)KERNEL_CODE_SELECTOR << 32U));
    wrmsr(MSR_LSTAR, (uintptr_t)port_syscall_entry);
    wrmsr(MSR_FMASK, RFLAGS_IF | RFLAGS_DF | RFLAGS_TF | RFLAGS_AC);
}

void port_irq_disable(void) { __asm__ volatile("cli" ::: "memory"); }

/*
 * QEMU's isa-debug-exit device makes QEMU exit with (v << 1) | 1, so 0x10, 0x11 and 0x12 become 33,
 * 35 and 37 (ADR 0006). On a machine without it, the write does nothing and the CPU halts.
 */
noreturn void port_power_off(enum port_outcome outcome) {
    port_irq_disable();

    uint8_t value = 0x12; /* an outcome out of range is reported as a panic */
    switch (outcome) {
    case PORT_OUTCOME_INIT_SUCCEEDED:
        value = 0x10;
        break;
    case PORT_OUTCOME_INIT_FAILED:
        value = 0x11;
        break;
    case PORT_OUTCOME_PANIC:
        value = 0x12;
        break;
    }
    outb(DEBUG_EXIT_PORT, value);

    for (;;) {
        __asm__ volatile("cli\n\t"
                         "hlt");
    }
}
