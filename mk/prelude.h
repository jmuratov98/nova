/*
 * Force-included (-include) into every kernel source, so a subsystem needs no include path for it.
 * It holds what exports and assembly symbols need to follow ADR 0003.
 *
 * Sources compile with -fvisibility=hidden. A subsystem marks what it exports with NOVA_EXPORT on
 * the declaration in its public header, and the build makes every other symbol local to the
 * subsystem. Assembly declares its symbols through the macros below, which emit .hidden unless
 * the symbol is exported, so raw .globl is rejected everywhere else.
 */

#ifndef NOVA_PRELUDE_H
#define NOVA_PRELUDE_H

#ifdef __ASSEMBLER__

/* clang-format off */

/* A symbol private to its subsystem: global, so that the subsystem's other objects reach it. */
.macro NOVA_FUNC name
    .globl \name
    .hidden \name
    .type \name, @function
\name:
.endm

/* A symbol that other subsystems may reference. */
.macro NOVA_EXPORT_FUNC name
    .globl \name
    .type \name, @function
\name:
.endm

.macro NOVA_END name
    .size \name, . - \name
.endm

/* clang-format on */

#else

#define NOVA_EXPORT __attribute__((visibility("default")))

#endif

#endif
