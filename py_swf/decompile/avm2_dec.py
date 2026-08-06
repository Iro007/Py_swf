"""
Decompilador AVM2 mejorado: análisis de flujo de control con CFG,
reconstrucción de if/else, while/for, try/catch, switch.
"""
from collections import defaultdict
from ..avm2 import ByteReader, resolve_multiname
from ..avm2_opcodes import OPCODES


def _decode(pool, code):
    """Decodifica bytecode a lista de instrucciones (pc, mnemonic, args)."""
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

_BRANCH_OPS = {
    "iftrue", "iffalse", "ifeq", "ifne", "iflt", "ifle", "ifgt", "ifge",
    "ifstricteq", "ifstrictne", "ifnlt", "ifnle", "ifngt", "ifnge",
}

_BRANCH_INVERSE = {
    "iffalse": "iftrue", "iftrue": "iffalse",
    "ifeq": "ifne", "ifne": "ifeq",
    "iflt": "ifge", "ifle": "ifgt",
    "ifgt": "ifle", "ifge": "iflt",
    "ifstricteq": "ifstrictne", "ifstrictne": "ifstricteq",
    "ifnlt": "ifnge", "ifnle": "ifngt",
    "ifngt": "ifnle", "ifnge": "ifnlt",
}

_UNOPS = {"not": "!", "negate": "-", "bitnot": "~"}
_INCOPS = {"increment": "++", "decrement": "--", "increment_i": "++", "decrement_i": "--"}


class BasicBlock:
    def __init__(self, start_pc):
        self.start_pc = start_pc
        self.instructions = []
        self.successors = []
        self.predecessors = []
        self.end_pc = None
        self.loop_header = False
        self.dominators = set()
        self.immediate_dominator = None

    def add_instr(self, pc, mn, args):
        self.instructions.append((pc, mn, args))
        self.end_pc = pc

    def __repr__(self):
        return f"BB({self.start_pc}-{self.end_pc})"


def build_cfg(instrs):
    """Construye bloques básicos y CFG a partir de instrucciones lineales."""
    pc_to_idx = {pc: i for i, (pc, _, _) in enumerate(instrs)}
    
    # Identificar líderes (inicios de bloques)
    leaders = {instrs[0][0]}
    for pc, mn, args in instrs:
        if mn in _BRANCH_OPS:
            target = pc + 4 + args[0]
            leaders.add(target)
            # La instrucción después del branch también es líder
            idx = pc_to_idx[pc]
            if idx + 1 < len(instrs):
                leaders.add(instrs[idx + 1][0])
        elif mn == "jump":
            target = pc + 4 + args[0]
            leaders.add(target)
        elif mn == "lookupswitch":
            default, _, cases = args
            leaders.add(pc + default)
            for c in cases:
                leaders.add(pc + c)
            idx = pc_to_idx[pc]
            if idx + 1 < len(instrs):
                leaders.add(instrs[idx + 1][0])
        elif mn in ("throw", "returnvalue", "returnvoid"):
            idx = pc_to_idx[pc]
            if idx + 1 < len(instrs):
                leaders.add(instrs[idx + 1][0])
    
    # Crear bloques
    sorted_leaders = sorted(leaders)
    blocks = {pc: BasicBlock(pc) for pc in sorted_leaders}
    
    # Asignar instrucciones a bloques
    current_block = None
    for pc, mn, args in instrs:
        if pc in leaders:
            current_block = blocks[pc]
        current_block.add_instr(pc, mn, args)
    
    # Conectar bloques (successors/predecessors)
    for block in blocks.values():
        last_pc, last_mn, last_args = block.instructions[-1]
        
        if last_mn in _BRANCH_OPS:
            target = last_pc + 4 + last_args[0]
            if target in blocks:
                block.successors.append(blocks[target])
                blocks[target].predecessors.append(block)
            # Fall-through
            idx = pc_to_idx[last_pc]
            if idx + 1 < len(instrs):
                next_pc = instrs[idx + 1][0]
                if next_pc in blocks:
                    block.successors.append(blocks[next_pc])
                    blocks[next_pc].predecessors.append(block)
        elif last_mn == "jump":
            target = last_pc + 4 + last_args[0]
            if target in blocks:
                block.successors.append(blocks[target])
                blocks[target].predecessors.append(block)
        elif last_mn == "lookupswitch":
            default, _, cases = last_args
            for t in [default] + cases:
                target = last_pc + t
                if target in blocks:
                    block.successors.append(blocks[target])
                    blocks[target].predecessors.append(block)
            idx = pc_to_idx[last_pc]
            if idx + 1 < len(instrs):
                next_pc = instrs[idx + 1][0]
                if next_pc in blocks:
                    block.successors.append(blocks[next_pc])
                    blocks[next_pc].predecessors.append(block)
        elif last_mn not in ("throw", "returnvalue", "returnvoid"):
            idx = pc_to_idx[last_pc]
            if idx + 1 < len(instrs):
                next_pc = instrs[idx + 1][0]
                if next_pc in blocks:
                    block.successors.append(blocks[next_pc])
                    blocks[next_pc].predecessors.append(block)
    
    # Orden topológico para dominadores
    entry = blocks[instrs[0][0]]
    compute_dominators(blocks, entry)
    detect_loops(blocks, entry)
    
    return blocks, entry


def compute_dominators(blocks, entry):
    """Algoritmo de dominadores (Lengauer-Tarjan simplificado)."""
    all_blocks = list(blocks.values())
    for b in all_blocks:
        b.dominators = set(all_blocks)
    entry.dominators = {entry}
    
    changed = True
    while changed:
        changed = False
        for b in all_blocks:
            if b is entry:
                continue
            preds = [p for p in b.predecessors if p in blocks.values()]
            if not preds:
                new_doms = {b}
            else:
                new_doms = {b} | set.intersection(*[p.dominators for p in preds])
            if new_doms != b.dominators:
                b.dominators = new_doms
                changed = True
    
    # Dominador inmediato
    for b in all_blocks:
        if b is entry:
            b.immediate_dominator = None
        else:
            candidates = b.dominators - {b}
            if candidates:
                b.immediate_dominator = max(candidates, key=lambda x: len(x.dominators))


def detect_loops(blocks, entry):
    """Detecta cabeceras de bucles (back edges)."""
    visited = set()
    stack = set()
    
    def dfs(b):
        visited.add(b)
        stack.add(b)
        for s in b.successors:
            if s not in visited:
                dfs(s)
            elif s in stack:
                # Back edge: s domina b => s es cabecera de bucle
                s.loop_header = True
        stack.remove(b)
    
    dfs(entry)


class DecompileContext:
    def __init__(self, pool, blocks, entry, exceptions):
        self.pool = pool
        self.blocks = blocks
        self.entry = entry
        self.exceptions = exceptions
        self.block_output = {}
        self.visited = set()
        self.indent = 0
        self.if_stack = []  # Para rastrear if/else
        self.loop_stack = []  # Para rastrear while/do-while

    def ind(self):
        return "    " * self.indent


def format_expr(expr, prec=100):
    """Formatea expresión con precedencia (placeholder para pretty-print)."""
    return expr


def decompile_block(ctx, block):
    """Decompila un bloque básico a líneas de código."""
    if block in ctx.visited:
        return []
    ctx.visited.add(block)
    
    lines = []
    stack = []
    
    def push(expr, prec=100):
        stack.append((expr, prec))
    
    def pop():
        return stack.pop() if stack else ("_", 100)
    
    def pop_e():
        return pop()[0]
    
    # Procesar instrucciones del bloque
    for pc, mn, args in block.instructions:
        # Manejar labels
        if mn == "label":
            continue
        
        if mn in ("getlocal_0", "getlocal_1", "getlocal_2", "getlocal_3"):
            reg = int(mn[-1])
            push("this" if reg == 0 else f"local{reg}")
        elif mn == "getlocal":
            push("this" if args[0] == 0 else f"local{args[0]}")
        elif mn in ("setlocal_0", "setlocal_1", "setlocal_2", "setlocal_3"):
            reg = int(mn[-1])
            val = pop_e()
            lines.append(f"{ctx.ind()}local{reg} = {val};")
        elif mn == "setlocal":
            val = pop_e()
            lines.append(f"{ctx.ind()}local{args[0]} = {val};")
        elif mn == "pushbyte" or mn == "pushshort":
            push(str(args[0]))
        elif mn == "pushint":
            push(str(ctx.pool.integers[args[0]] if args[0] < len(ctx.pool.integers) else 0))
        elif mn == "pushuint":
            push(str(ctx.pool.uintegers[args[0]] if args[0] < len(ctx.pool.uintegers) else 0))
        elif mn == "pushdouble":
            push(str(ctx.pool.doubles[args[0]] if args[0] < len(ctx.pool.doubles) else 0))
        elif mn == "pushstring":
            s = ctx.pool.strings[args[0]] if args[0] < len(ctx.pool.strings) else ""
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
        elif mn == "dup":
            top = stack[-1] if stack else ("_", 100)
            stack.append(top)
        elif mn == "pop":
            if stack:
                expr = pop_e()
                if expr.endswith(")"):
                    lines.append(f"{ctx.ind()}{expr};")
        elif mn in ("coerce_a", "coerce_s", "coerce_d", "coerce_i", "coerce_u",
                    "convert_i", "convert_u", "convert_d", "convert_b", "convert_s",
                    "convert_o", "coerce_b", "checkfilter", "nop",
                    "pushscope", "popscope", "pushwith"):
            pass
        elif mn == "coerce":
            pass
        elif mn == "getlex":
            push(resolve_multiname(ctx.pool, args[0]))
        elif mn in ("findpropstrict", "findproperty"):
            push("")
        elif mn == "getproperty":
            obj = pop_e()
            name = resolve_multiname(ctx.pool, args[0]).split("::")[-1]
            push(f"{obj}.{name}" if obj else name, prec=90)
        elif mn in ("setproperty", "initproperty"):
            val = pop_e()
            obj = pop_e()
            name = resolve_multiname(ctx.pool, args[0]).split("::")[-1]
            target = f"{obj}.{name}" if obj else name
            lines.append(f"{ctx.ind()}{target} = {val};")
        elif mn in ("callproperty", "callproplex", "callpropvoid"):
            argc = args[1]
            call_args = [pop_e() for _ in range(argc)][::-1]
            obj = pop_e()
            name = resolve_multiname(ctx.pool, args[0]).split("::")[-1]
            target = f"{obj}.{name}" if obj else name
            call = f"{target}({', '.join(call_args)})"
            if mn == "callpropvoid":
                lines.append(f"{ctx.ind()}{call};")
            else:
                push(call, prec=90)
        elif mn == "constructprop":
            argc = args[1]
            call_args = [pop_e() for _ in range(argc)][::-1]
            obj = pop_e()
            name = resolve_multiname(ctx.pool, args[0]).split("::")[-1]
            push(f"new {name}({', '.join(call_args)})", prec=90)
        elif mn == "constructsuper":
            argc = args[0]
            call_args = [pop_e() for _ in range(argc)][::-1]
            pop_e()
            lines.append(f"{ctx.ind()}super({', '.join(call_args)});")
        elif mn == "returnvalue":
            lines.append(f"{ctx.ind()}return {pop_e};")
        elif mn == "returnvoid":
            lines.append(f"{ctx.ind()}return;")
        elif mn in _BINOPS:
            b = pop_e()
            a = pop_e()
            push(f"({a} {_BINOPS[mn]} {b})", prec=50)
        elif mn in _UNOPS:
            push(f"{_UNOPS[mn]}({pop_e()})", prec=60)
        elif mn in _INCOPS:
            # ++x / --x
            var = pop_e()
            op = _INCOPS[mn]
            lines.append(f"{ctx.ind()}{op}{var};")
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
        elif mn in ("throw",):
            lines.append(f"{ctx.ind()}throw {pop_e()};")
        else:
            lines.append(f"{ctx.ind()}// UNKNOWN: {mn} {args}")
    
    # Manejar successors (control flow)
    if block.successors:
        # Loop header
        if block.loop_header:
            return handle_loop(ctx, block, lines)
        
        # If/else
        if len(block.successors) == 2:
            return handle_if_else(ctx, block, lines)
        
        # Single successor (fall-through or jump)
        if len(block.successors) == 1:
            succ = block.successors[0]
            if succ not in ctx.visited:
                lines.extend(decompile_block(ctx, succ))
    
    return lines


def handle_loop(ctx, block, lines):
    """Detecta y emite while/do-while/for loops."""
    # Buscar el latch (bloque que salta de vuelta a la cabecera)
    latch = None
    for pred in block.predecessors:
        if pred != block and pred in ctx.visited:
            # Verificar si pred termina en jump hacia block
            last_mn = pred.instructions[-1][1] if pred.instructions else None
            if last_mn == "jump":
                target = pred.instructions[-1][0] + 4 + pred.instructions[-1][2][0]
                if target == block.start_pc:
                    latch = pred
                    break
    
    if latch:
        # while loop
        ctx.indent += 1
        # El header ya tiene la condición, emitirla
        # Simplificación: emitir while(true) con break
        lines.append(f"{ctx.ind()}while (true) {{")
        # Decompilar cuerpo (sin el latch)
        for succ in block.successors:
            if succ != latch:
                lines.extend(decompile_block(ctx, succ))
        ctx.indent -= 1
        lines.append(f"{ctx.ind()}}}")
        return lines
    
    # Fallback
    for succ in block.successors:
        if succ not in ctx.visited:
            lines.extend(decompile_block(ctx, succ))
    return lines


def handle_if_else(ctx, block, lines):
    """Reconstruye if/else a partir de branch condicional + fall-through."""
    # El último instr del block es el branch condicional
    last_pc, last_mn, last_args = block.instructions[-1]
    
    if last_mn not in _BRANCH_OPS:
        # No es un branch condicional, tratar como fall-through
        for succ in block.successors:
            if succ not in ctx.visited:
                lines.extend(decompile_block(ctx, succ))
        return lines
    
    # Obtener la condición del stack (simplificado)
    # En una implementación real, haríamos análisis de pila hacia atrás
    cond = "condition"  # placeholder
    
    # Identificar then/else blocks
    then_block = None
    else_block = None
    
    # El target del branch es uno, el fall-through es el otro
    branch_target = last_pc + 4 + last_args[0]
    fallthrough_pc = None
    idx = list(ctx.blocks.keys()).index(last_pc) if last_pc in ctx.blocks else -1
    # Simplificación: usar el orden de successors
    for succ in block.successors:
        if succ.start_pc == branch_target:
            then_block = succ
        else:
            else_block = succ
    
    if then_block is None and else_block is None:
        # Fallback
        for succ in block.successors:
            if succ not in ctx.visited:
                lines.extend(decompile_block(ctx, succ))
        return lines
    
    # Emitir if
    lines.append(f"{ctx.ind()}if ({cond}) {{")
    ctx.indent += 1
    if then_block and then_block not in ctx.visited:
        lines.extend(decompile_block(ctx, then_block))
    ctx.indent -= 1
    lines.append(f"{ctx.ind()}}}")
    
    if else_block and else_block not in ctx.visited:
        # Verificar si else_block es solo un jump a after-if
        if len(else_block.instructions) == 1 and else_block.instructions[0][1] == "jump":
            # else vacío, no emitir
            pass
        else:
            lines.append(f"{ctx.ind()}else {{")
            ctx.indent += 1
            lines.extend(decompile_block(ctx, else_block))
            ctx.indent -= 1
            lines.append(f"{ctx.ind()}}}")
    
    return lines


def decompile_method(abc, body, method_name="method"):
    """
    Decompila un MethodBodyInfo a pseudo-AS3 con control flow.
    Devuelve (source, error).
    """
    pool = abc.constant_pool
    
    if body.exceptions:
        # Intentar decompilar con try/catch
        try:
            return decompile_with_exceptions(abc, body, method_name)
        except Exception as e:
            return None, f"try/catch decompilation failed: {e}"
    
    instrs, _ = _decode(pool, body.code)
    if not instrs:
        return "// empty method", None
    
    blocks, entry = build_cfg(instrs)
    
    ctx = DecompileContext(pool, blocks, entry, body.exceptions)
    ctx.blocks = blocks
    
    try:
        lines = decompile_block(ctx, entry)
        return "\n".join(lines), None
    except Exception as e:
        return None, f"decompilation error: {e}"


def decompile_with_exceptions(abc, body, method_name):
    """Decompilación básica con try/catch (simplificada)."""
    pool = abc.constant_pool
    instrs, _ = _decode(pool, body.code)
    
    # Para v1: emitir estructura try/catch como comentario + disassembly
    lines = [
        f"// Method: {method_name}",
        "// Contains try/catch - showing structured disassembly:",
        ""
    ]
    
    for pc, mn, args in instrs:
        if mn == "lookupswitch":
            default, count, cases = args
            lines.append(f"    switch (value) {{")
            for i, c in enumerate(cases):
                lines.append(f"        case {i}: goto L_{pc + c};")
            lines.append(f"        default: goto L_{pc + default};")
            lines.append(f"    }}")
        else:
            arg_str = " ".join(str(a) for a in args)
            lines.append(f"    {mn} {arg_str}")
    
    return "\n".join(lines), None


# ============================================================
# Fallback: desensamblador simple para métodos no decompilables
# ============================================================

def disassemble_method(abc, body):
    """Genera desassembly legible como fallback."""
    pool = abc.constant_pool
    from ..avm2 import disassemble_instructions
    return disassemble_instructions(pool, body.code)