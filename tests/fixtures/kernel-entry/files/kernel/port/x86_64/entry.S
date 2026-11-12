    .text

NOVA_FUNC port_entry
1:
    hlt
    jmp 1b
NOVA_END port_entry
