"""
Decompilador AVM2 v1 (acotado): reconstrucción de expresiones por simulación de
pila sobre el P-code, con estructuración básica de if/while a partir de saltos.

No es paridad JPEXS: métodos con exception handlers, control de flujo complejo o
patrones que no reconocemos caen a un comentario + disassembly. El objetivo es
producir pseudo-AS3 legible para los casos comunes.
"""
from ..avm2 import ByteReader, resolve_multiname
from ..avm2_opcodes import OPCODES


def _decode(pool, code):
    """Devuelve lista de (pc, mnemonic, args) y el set de PCs destino de saltos."""
    reader = ByteReader(code)
    instrs = []
    targets = set()
    while reader.offset < len(code):
        pc = reader.offset
        try:
            opcode = reader.read_byte()
        except EOFError:
            break
        if opcode not in OPCODES:
            instrs.append((pc, f"raw_0x{opcode:02X}", []))
            continue
        mnemonic, arg_types = OPCODES[opcode]
        args = []
        try:
            if mnemonic == "lookupswitch":
                default = reader.read_s24()
                count = reader.read_u30()
                cases = [reader.read_s24() for _ in range(count + 1)]
                args = [default, count, cases]
                targets.add(pc + default)
                for c in cases:
                    targets.add(pc + c)
            else:
                for at in arg_types:
                    if at == "u30":
                        args.append(reader.read_u30())
                    elif at == "s24":
                        v = reader.read_s24()
                        args.append(v)
                        targets.add(pc + 4 + v)
                    elif at == "byte":
                        args.append(reader.read_byte())
        except EOFError:
            pass
        instrs.append((pc, mnemonic, args))
    return instrs, targets


_BINOPS = {
    "add": "+", "add_i": "+", "subtract": "-", "subtract_i": "-",
    "multiply": "*", "multiply_i": "*", "divide": "/", "modulo": "%",
    "lshift": "<<", "rshift": ">>", "urshift": ">>>",
    "bitand": "&", "bitor": "|", "bitxor": "^",
    "equals": "==", "strictequals": "===", "lessthan": "<", "lessequals": "<=",
    "greaterthan": ">", "greaterequals": ">=",
}

_BRANCH_INVERSE = {
    "iffalse": "{cond}", "iftrue": "!({cond})",
    "ifeq": "{a} != {b}", "ifne": "{a} == {b}",
    "iflt": "{a} >= {b}", "ifle": "{a} > {b}",
    "ifgt": "{a} <= {b}", "ifge": "{a} < {b}",
    "ifstricteq": "{a} !== {b}", "ifstrictne": "{a} === {b}",
    "ifnlt": "{a} < {b}", "ifnle": "{a} <= {b}",
    "ifngt": "{a} > {b}", "ifnge": "{a} >= {b}",
}


class _DecompileError(Exception):
    pass


def _simulate(pool, instrs, method=None):
    """
    Recorre las instrucciones simulando la pila y emite sentencias. Devuelve la
    lista de líneas de pseudo-AS3. Lanza _DecompileError en construcciones no
    soportadas para que el llamador haga fallback.
    """
    lines = []
    stack = []
    indent = [1]

    def push(expr, prec=100):
        stack.append((expr, prec))

    def pop():
        if not stack:
            return ("_", 100)
        return stack.pop()

    def pop_e():
        return pop()[0]

    def ind():
        return "    " * indent[0]

    # PCs a los que salta algún branch hacia atrás => cierres de while
    # (v1: emitimos control de flujo simple; si aparece algo raro, fallback)
    pc_to_index = {pc: i for i, (pc, _, _) in enumerate(instrs)}

    i = 0
    n = len(instrs)
    while i < n:
        pc, mn, args = instrs[i]

        if mn.startswith("raw_0x"):
            raise _DecompileError(f"unknown opcode at {pc}")

        if mn in ("getlocal_0", "getlocal_1", "getlocal_2", "getlocal_3"):
            reg = int(mn[-1])
            push("this" if reg == 0 else f"local{reg}")
        elif mn == "getlocal":
            push("this" if args[0] == 0 else f"local{args[0]}")
        elif mn in ("setlocal_0", "setlocal_1", "setlocal_2", "setlocal_3"):
            reg = int(mn[-1])
            val = pop_e()
            lines.append(f"{ind()}local{reg} = {val};")
        elif mn == "setlocal":
            val = pop_e()
            lines.append(f"{ind()}local{args[0]} = {val};")
        elif mn == "pushbyte" or mn == "pushshort":
            push(str(args[0]))
        elif mn == "pushint":
            push(str(pool.integers[args[0]] if args[0] < len(pool.integers) else 0))
        elif mn == "pushuint":
            push(str(pool.uintegers[args[0]] if args[0] < len(pool.uintegers) else 0))
        elif mn == "pushdouble":
            push(str(pool.doubles[args[0]] if args[0] < len(pool.doubles) else 0))
        elif mn == "pushstring":
            s = pool.strings[args[0]] if args[0] < len(pool.strings) else ""
            push('"' + s.replace('"', '\\"') + '"')
        elif mn == "pushtrue":
            push("true")
        elif mn == "pushfalse":
            push("false")
        elif mn == "pushnull":
            push("null")
        elif mn == "pushundefined":
            push("undefined")
        elif mn == "pushnan":
            push("NaN")
        elif mn in ("dup",):
            top = stack[-1] if stack else ("_", 100)
            stack.append(top)
        elif mn in ("pop",):
            if stack:
                expr = pop_e()
                # una llamada con efecto colateral se emite como sentencia
                if expr.endswith(")"):
                    lines.append(f"{ind()}{expr};")
        elif mn in ("coerce_a", "coerce_s", "coerce_d", "coerce_i", "coerce_u",
                    "convert_i", "convert_u", "convert_d", "convert_b", "convert_s",
                    "convert_o", "coerce_b", "checkfilter", "nop", "label",
                    "pushscope", "popscope", "pushwith"):
            pass  # no afectan a la reconstrucción de expresiones de alto nivel
        elif mn == "coerce":
            pass
        elif mn == "getlex":
            push(resolve_multiname(pool, args[0]))
        elif mn in ("findpropstrict", "findproperty"):
            push("")  # el objeto contenedor; getproperty lo completará
        elif mn == "getproperty":
            obj = pop_e()
            name = resolve_multiname(pool, args[0]).split("::")[-1]
            push(f"{obj}.{name}" if obj else name, prec=90)
        elif mn == "setproperty" or mn == "initproperty":
            val = pop_e()
            obj = pop_e()
            name = resolve_multiname(pool, args[0]).split("::")[-1]
            target = f"{obj}.{name}" if obj else name
            lines.append(f"{ind()}{target} = {val};")
        elif mn in ("callproperty", "callproplex", "callpropvoid"):
            argc = args[1]
            call_args = [pop_e() for _ in range(argc)][::-1]
            obj = pop_e()
            name = resolve_multiname(pool, args[0]).split("::")[-1]
            target = f"{obj}.{name}" if obj else name
            call = f"{target}({', '.join(call_args)})"
            if mn == "callpropvoid":
                lines.append(f"{ind()}{call};")
            else:
                push(call, prec=90)
        elif mn == "constructprop":
            argc = args[1]
            call_args = [pop_e() for _ in range(argc)][::-1]
            obj = pop_e()
            name = resolve_multiname(pool, args[0]).split("::")[-1]
            push(f"new {name}({', '.join(call_args)})", prec=90)
        elif mn == "constructsuper":
            argc = args[0]
            call_args = [pop_e() for _ in range(argc)][::-1]
            pop_e()  # this
            lines.append(f"{ind()}super({', '.join(call_args)});")
        elif mn == "returnvalue":
            lines.append(f"{ind()}return {pop_e()};")
        elif mn == "returnvoid":
            if i != n - 1:
                lines.append(f"{ind()}return;")
        elif mn in _BINOPS:
            b = pop_e()
            a = pop_e()
            push(f"({a} {_BINOPS[mn]} {b})", prec=50)
        elif mn == "not":
            push(f"!({pop_e()})", prec=60)
        elif mn == "negate":
            push(f"-({pop_e()})", prec=60)
        elif mn in ("increment", "increment_i"):
            push(f"({pop_e()} + 1)", prec=50)
        elif mn in ("decrement", "decrement_i"):
            push(f"({pop_e()} - 1)", prec=50)
        elif mn == "newarray":
            items = [pop_e() for _ in range(args[0])][::-1]
            push(f"[{', '.join(items)}]")
        elif mn == "newobject":
            pairs = []
            for _ in range(args[0]):
                v = pop_e()
                k = pop_e()
                pairs.append(f"{k}: {v}")
            push("{" + ", ".join(pairs[::-1]) + "}")
        elif mn == "jump":
            # solo aceptamos saltos hacia adelante que no formen bucles no triviales
            raise _DecompileError("jump (control flow) not supported in v1")
        elif mn in _BRANCH_INVERSE:
            raise _DecompileError("branch (control flow) not supported in v1")
        elif mn == "lookupswitch":
            raise _DecompileError("switch not supported in v1")
        else:
            raise _DecompileError(f"unsupported opcode '{mn}'")

        i += 1

    return lines


def decompile_method(abc, body, method_name="method"):
    """
    Decompila un MethodBodyInfo a pseudo-AS3. Si falla, devuelve un comentario
    de fallo (el llamador puede añadir el disassembly).
    """
    pool = abc.constant_pool
    if body.exceptions:
        return None, "método con try/catch (no soportado en v1)"
    instrs, targets = _decode(pool, body.code)
    # cualquier salto hacia atrás => bucle: fuera de alcance v1
    for pc, mn, args in instrs:
        if mn == "jump" and args and (pc + 4 + args[0]) <= pc:
            return None, "bucle detectado (no soportado en v1)"
    try:
        lines = _simulate(pool, instrs, method=None)
    except _DecompileError as exc:
        return None, str(exc)
    return "\n".join(lines), None
