from .avm2 import resolve_multiname


def decompile_method_to_as3(abc, mb, method_name="method"):
    """Create a readable, structured AS3-like pseudo-code from AVM2 bytecode.

    This is intentionally lightweight and aimed at producing understandable
    output for common simple methods rather than full-featured decompilation.
    """
    method_info = abc.methods[mb.method] if mb.method < len(abc.methods) else None
    return_type = "*"
    if method_info is not None and method_info.return_type != 0:
        return_type = resolve_multiname(abc.constant_pool, method_info.return_type)

    lines = []
    lines.append(f"function {method_name}():{return_type} {{")

    stack = []
    pending_target = None
    for opcode, args in _decode_simple_instructions(abc.constant_pool, mb.code):
        if opcode == "findpropstrict":
            pending_target = args[0]
        elif opcode == "pushstring":
            stack.append(("string", args[0]))
        elif opcode == "pushint":
            stack.append(("int", args[0]))
        elif opcode == "pushdouble":
            stack.append(("double", args[0]))
        elif opcode in {"callproperty", "callpropvoid", "callproplex"}:
            target = pending_target or args[0]
            arg_count = int(args[1]) if len(args) > 1 else 0
            call_args = []
            for _ in range(arg_count):
                if stack:
                    value_kind, value = stack.pop()
                    if value_kind == "string":
                        call_args.append(f'"{str(value).replace("\\", "\\\\").replace("\"", "\\\"")}"')
                    else:
                        call_args.append(str(value))
                else:
                    call_args.append("arg")
            call_args.reverse()
            lines.append(f"    {target}({', '.join(call_args)});")
            pending_target = None
        elif opcode == "returnvoid":
            lines.append("    return;")
        elif opcode == "getlocal_0":
            lines.append("    var self = this;")
        else:
            lines.append(f"    // {opcode} {args}")

    lines.append("}")
    return "\n".join(lines)


def _decode_simple_instructions(pool, code):
    from .avm2 import ByteReader, OPCODES

    reader = ByteReader(code)
    instructions = []

    while reader.offset < len(code):
        opcode_byte = reader.read_byte()
        if opcode_byte not in OPCODES:
            instructions.append(("unknown", []))
            continue

        mnemonic, arg_types = OPCODES[opcode_byte]
        args = []
        for arg_type in arg_types:
            if arg_type == "u30":
                value = reader.read_u30()
                if mnemonic == "pushstring":
                    args.append(pool.strings[value] if value < len(pool.strings) else "")
                elif mnemonic in {"findpropstrict", "getproperty", "setproperty", "callproperty", "callpropvoid", "callproplex"}:
                    args.append(resolve_multiname(pool, value))
                else:
                    args.append(value)
            elif arg_type == "s24":
                args.append(reader.read_s24())
            elif arg_type == "byte":
                args.append(reader.read_byte())
        instructions.append((mnemonic, args))

    return instructions
