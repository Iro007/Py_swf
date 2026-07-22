"""
Decompilador AVM1 v1: simulación de pila sobre el disassembly para producir
pseudo-ActionScript 2 legible en código lineal (push/get/set/call, trace,
operadores, if simple). Construcciones no reconocidas se emiten como comentario.
"""
import struct

from ..avm1 import AVM1_OPCODES, parse_push_values


def _decode(data):
    """Devuelve lista de (pc, code, payload) y set de PCs destino de branch."""
    actions = []
    targets = set()
    i = 0
    while i < len(data):
        pc = i
        code = data[i]
        i += 1
        if code == 0:
            actions.append((pc, 0, b""))
            break
        if code < 0x80:
            actions.append((pc, code, b""))
        else:
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i + 2], "little")
            i += 2
            payload = data[i:i + length]
            i += length
            actions.append((pc, code, payload))
            if code in (0x99, 0x9D):
                off = int.from_bytes(payload[0:2], "little", signed=True)
                targets.add(pc + 5 + off)
    return actions, targets


_BINOPS = {
    "add": "+", "add2": "+", "subtract": "-", "multiply": "*", "divide": "/",
    "modulo": "%", "bit_and": "&", "bit_or": "|", "bit_xor": "^",
    "bit_lshift": "<<", "bit_rshift": ">>", "bit_urshift": ">>>",
    "equals": "==", "equals2": "==", "strict_equals": "===",
    "less_than": "<", "less2": "<", "greater": ">", "and": "&&", "or": "||",
    "string_equals": "==", "string_add": "+",
}


def _push_token(v):
    """Convierte un token de parse_push_values a expresión AS."""
    if v.startswith("c:") or v.startswith("r:"):
        return None  # constant-pool / registro: resueltos por contexto
    return v


def decompile_avm1(data, constant_pool=None):
    """
    Decompila un bloque de acciones AVM1 a pseudo-AS2. `constant_pool` es la
    lista de strings de un ConstantPool action previo (para resolver c:N).
    Devuelve (source, error). Ante lo no soportado, incluye comentarios inline.
    """
    actions, targets = _decode(data)
    pool = list(constant_pool or [])
    lines = []
    stack = []
    unsupported = 0

    def push(x):
        stack.append(x)

    def pop():
        return stack.pop() if stack else "undefined"

    for pc, code, payload in actions:
        if pc in targets:
            lines.append(f"L_{pc}:")
        mn = AVM1_OPCODES.get(code)

        if mn == "constant_pool":
            count = int.from_bytes(payload[0:2], "little")
            off = 2
            pool = []
            for _ in range(count):
                end = payload.find(b"\x00", off)
                if end == -1:
                    break
                pool.append(payload[off:end].decode("utf-8", errors="replace"))
                off = end + 1
        elif mn == "push":
            for tok in parse_push_values(payload):
                if tok.startswith("c:"):
                    idx = int(tok[2:])
                    push('"' + (pool[idx] if idx < len(pool) else f"c{idx}") + '"')
                elif tok.startswith("r:"):
                    push(f"r{tok[2:]}")
                else:
                    push(tok)
        elif mn == "get_variable":
            name = pop()
            push(f"{name[1:-1] if name.startswith(chr(34)) else name}")
        elif mn == "set_variable":
            val = pop()
            name = pop()
            nm = name[1:-1] if name.startswith('"') else name
            lines.append(f"{nm} = {val};")
        elif mn == "get_member":
            member = pop()
            obj = pop()
            mm = member[1:-1] if member.startswith('"') else f"[{member}]"
            push(f"{obj}.{mm}" if member.startswith('"') else f"{obj}[{member}]")
        elif mn == "set_member":
            val = pop()
            member = pop()
            obj = pop()
            if member.startswith('"'):
                lines.append(f"{obj}.{member[1:-1]} = {val};")
            else:
                lines.append(f"{obj}[{member}] = {val};")
        elif mn == "trace":
            lines.append(f"trace({pop()});")
        elif mn in _BINOPS:
            b = pop()
            a = pop()
            push(f"({a} {_BINOPS[mn]} {b})")
        elif mn == "not":
            push(f"!({pop()})")
        elif mn == "call_function":
            name = pop()
            argc = pop()
            try:
                n = int(argc)
            except ValueError:
                n = 0
            call_args = [pop() for _ in range(n)][::-1]
            nm = name[1:-1] if name.startswith('"') else name
            push(f"{nm}({', '.join(call_args)})")
        elif mn == "call_method":
            method = pop()
            obj = pop()
            argc = pop()
            try:
                n = int(argc)
            except ValueError:
                n = 0
            call_args = [pop() for _ in range(n)][::-1]
            mm = method[1:-1] if method.startswith('"') else method
            call = f"{obj}.{mm}({', '.join(call_args)})"
            push(call)
        elif mn == "pop":
            if stack:
                expr = pop()
                if expr.endswith(")"):
                    lines.append(f"{expr};")
        elif mn == "define_local":
            val = pop()
            name = pop()
            nm = name[1:-1] if name.startswith('"') else name
            lines.append(f"var {nm} = {val};")
        elif mn == "if":
            off = int.from_bytes(payload[0:2], "little", signed=True)
            target = pc + 5 + off
            lines.append(f"if ({pop()}) goto L_{target};")
        elif mn == "jump":
            off = int.from_bytes(payload[0:2], "little", signed=True)
            lines.append(f"goto L_{pc + 5 + off};")
        elif mn in ("stop", "play", "next_frame", "prev_frame", "stop_sounds"):
            lines.append(f"{mn}();")
        elif mn == "goto_frame":
            frame = int.from_bytes(payload[0:2], "little")
            lines.append(f"gotoAndStop({frame});")
        elif mn == "return":
            lines.append(f"return {pop()};" if stack else "return;")
        elif code == 0:
            pass  # end
        else:
            # acción sin regla de alto nivel: dejar rastro sin romper
            unsupported += 1
            lines.append(f"// {mn or f'action_0x{code:02X}'}")

    error = None
    if unsupported > len(actions) // 2:
        error = "demasiadas acciones sin decompilar; ver disassembly"
    return "\n".join(lines), error
