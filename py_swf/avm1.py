import struct

AVM1_OPCODES = {
    0x04: "next_frame",
    0x05: "prev_frame",
    0x06: "play",
    0x07: "stop",
    0x08: "toggle_quality",
    0x09: "stop_sounds",
    0x0A: "add",
    0x0B: "subtract",
    0x0C: "multiply",
    0x0D: "divide",
    0x0E: "equals",
    0x0F: "less_than",
    0x10: "and",
    0x11: "or",
    0x12: "not",
    0x13: "string_equals",
    0x14: "string_length",
    0x15: "string_extract",
    0x17: "pop",
    0x18: "to_integer",
    0x1C: "get_variable",
    0x1D: "set_variable",
    0x20: "set_target2",
    0x21: "string_add",
    0x22: "get_property",
    0x23: "set_property",
    0x24: "clone_sprite",
    0x25: "remove_sprite",
    0x26: "trace",
    0x27: "start_drag",
    0x28: "end_drag",
    0x29: "string_less_than",
    0x2A: "throw",
    0x2B: "cast_op",
    0x2C: "implements_op",
    0x30: "random_number",
    0x31: "mb_string_length",
    0x32: "char_to_ascii",
    0x33: "ascii_to_char",
    0x34: "get_time",
    0x35: "mb_string_extract",
    0x36: "mb_char_to_ascii",
    0x37: "mb_ascii_to_char",
    0x3A: "delete_var",
    0x3B: "delete_obj",
    0x3C: "define_local",
    0x3D: "define_local2",
    0x3E: "end_drag",
    0x3F: "call_method",
    0x40: "new_method",
    0x41: "instance_of",
    0x42: "type_of",
    0x43: "target_path",
    0x44: "enumerate",
    0x45: "new_object",
    0x46: "enumerate2",
    0x47: "bit_and",
    0x48: "bit_or",
    0x49: "bit_xor",
    0x4A: "bit_lshift",
    0x4B: "bit_rshift",
    0x4C: "bit_urshift",
    0x4D: "strict_equals",
    0x4E: "greater_than",
    0x50: "string_greater_than",
    0x52: "extends_op",
    # Multi-byte actions
    0x81: "goto_frame",
    0x83: "get_url",
    0x87: "store_register",
    0x88: "constant_pool",
    0x89: "strict_mode",
    0x8A: "wait_for_frame",
    0x8B: "set_target",
    0x8C: "goto_label",
    0x8D: "wait_for_frame2",
    0x96: "push",
    0x99: "jump",
    0x9A: "get_url2",
    0x9D: "if",
    0x9F: "goto_frame2",
}

AVM1_MNEMONICS = {v: k for k, v in AVM1_OPCODES.items()}

def parse_push_values(data):
    values = []
    offset = 0
    while offset < len(data):
        if offset >= len(data):
            break
        v_type = data[offset]
        offset += 1
        if v_type == 0:  # String
            end = data.find(b"\x00", offset)
            if end == -1:
                end = len(data)
            s = data[offset:end].decode("utf-8", errors="ignore")
            offset = end + 1
            values.append(f'"{s}"')
        elif v_type == 1:  # Float
            if offset + 4 > len(data): break
            f_val = struct.unpack("<f", data[offset:offset+4])[0]
            offset += 4
            values.append(str(f_val))
        elif v_type == 2:  # Null
            values.append("null")
        elif v_type == 3:  # Undefined
            values.append("undefined")
        elif v_type == 4:  # Register
            if offset + 1 > len(data): break
            reg = data[offset]
            offset += 1
            values.append(f"r:{reg}")
        elif v_type == 5:  # Boolean
            if offset + 1 > len(data): break
            b_val = data[offset]
            offset += 1
            values.append("true" if b_val else "false")
        elif v_type == 6:  # Double
            if offset + 8 > len(data): break
            d_val = struct.unpack("<d", data[offset:offset+8])[0]
            offset += 8
            values.append(str(d_val))
        elif v_type == 7:  # Integer
            if offset + 4 > len(data): break
            i_val = int.from_bytes(data[offset:offset+4], "little", signed=True)
            offset += 4
            values.append(str(i_val))
        elif v_type == 8:  # Constant index 8
            if offset + 1 > len(data): break
            idx = data[offset]
            offset += 1
            values.append(f"c:{idx}")
        elif v_type == 9:  # Constant index 16
            if offset + 2 > len(data): break
            idx = int.from_bytes(data[offset:offset+2], "little")
            offset += 2
            values.append(f"c:{idx}")
        else:
            break
    return values

def disassemble_avm1(data):
    # Pass 1: Decode actions to discover label targets
    actions = []
    target_pcs = set()
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
            length = int.from_bytes(data[i:i+2], "little")
            i += 2
            act_data = data[i:i+length]
            i += length
            actions.append((pc, code, act_data))
            
            # Check for branches
            if code in (0x99, 0x9D):  # jump, if
                offset = int.from_bytes(act_data[0:2], "little", signed=True)
                target_pc = pc + 5 + offset
                target_pcs.add(target_pc)
                
    # Pass 2: Format disasm text
    lines = []
    for pc, code, act_data in actions:
        if pc in target_pcs:
            lines.append(f"L_{pc}:")
            
        if code == 0:
            lines.append("    end")
            continue
            
        mnemonic = AVM1_OPCODES.get(code, f"raw_action_0x{code:02X}")
        
        if code < 0x80:
            lines.append(f"    {mnemonic}")
        else:
            # Multi-byte actions
            formatted = []
            if code == 0x96:  # push
                push_vals = parse_push_values(act_data)
                formatted.append(" ".join(push_vals))
            elif code in (0x99, 0x9D):  # jump, if
                offset = int.from_bytes(act_data[0:2], "little", signed=True)
                target_pc = pc + 5 + offset
                formatted.append(f"L_{target_pc}")
            elif code == 0x81:  # goto_frame
                frame = int.from_bytes(act_data[0:2], "little")
                formatted.append(str(frame))
            elif code == 0x83:  # get_url
                url_end = act_data.find(b"\x00")
                url = act_data[:url_end].decode("utf-8", errors="ignore")
                target_end = act_data.find(b"\x00", url_end + 1)
                target = act_data[url_end+1:target_end].decode("utf-8", errors="ignore")
                formatted.append(f'"{url}" "{target}"')
            elif code == 0x87:  # store_register
                formatted.append(str(act_data[0]))
            elif code == 0x88:  # constant_pool
                count = int.from_bytes(act_data[0:2], "little")
                offset = 2
                pool_strings = []
                for _ in range(count):
                    end = act_data.find(b"\x00", offset)
                    if end == -1: break
                    pool_strings.append('"' + act_data[offset:end].decode("utf-8", errors="ignore") + '"')
                    offset = end + 1
                formatted.append("[" + ", ".join(pool_strings) + "]")
            elif code == 0x89:  # strict_mode
                formatted.append(str(act_data[0]))
            elif code == 0x8A:  # wait_for_frame
                frame = int.from_bytes(act_data[0:2], "little")
                skip = act_data[2]
                formatted.append(f"{frame} {skip}")
            elif code == 0x8B:  # set_target
                target = act_data[:-1].decode("utf-8", errors="ignore")
                formatted.append(f'"{target}"')
            elif code == 0x8C:  # goto_label
                label = act_data[:-1].decode("utf-8", errors="ignore")
                formatted.append(f'"{label}"')
            elif code == 0x8D:  # wait_for_frame2
                formatted.append(str(act_data[0]))
            elif code == 0x9A:  # get_url2
                formatted.append(str(act_data[0]))
            elif code == 0x9F:  # goto_frame2
                flags = act_data[0]
                bias = int.from_bytes(act_data[1:3], "little") if len(act_data) > 1 else 0
                formatted.append(f"{flags} {bias}")
            else:
                # Raw hex representation of unknown multibyte payload
                formatted.append(act_data.hex())
                
            args_str = " " + " ".join(formatted) if formatted else ""
            lines.append(f"    {mnemonic}{args_str}")
            
    return "\n".join(lines)

def serialize_push_value(val_str):
    val_str = val_str.strip()
    if val_str.startswith('"') and val_str.endswith('"'):
        s = val_str[1:-1]
        s_bytes = s.encode("utf-8") + b"\x00"
        return b"\x00" + s_bytes
    elif val_str == "null":
        return b"\x02"
    elif val_str == "undefined":
        return b"\x03"
    elif val_str.startswith("r:"):
        reg = int(val_str[2:])
        return b"\x04" + bytes([reg])
    elif val_str == "true":
        return b"\x05\x01"
    elif val_str == "false":
        return b"\x05\x00"
    elif val_str.startswith("c:"):
        idx = int(val_str[2:])
        if idx < 256:
            return b"\x08" + bytes([idx])
        else:
            return b"\x09" + idx.to_bytes(2, "little")
            
    if "." in val_str:
        try:
            d_val = float(val_str)
            return b"\x06" + struct.pack("<d", d_val)
        except ValueError:
            return b"\x00" + val_str.encode("utf-8") + b"\x00"
    else:
        try:
            i_val = int(val_str)
            if -2147483648 <= i_val <= 2147483647:
                return b"\x07" + i_val.to_bytes(4, "little", signed=True)
            else:
                return b"\x06" + struct.pack("<d", float(i_val))
        except ValueError:
            return b"\x00" + val_str.encode("utf-8") + b"\x00"

def assemble_avm1(text):
    lines = text.strip().split("\n")
    instructions = []
    
    label_def = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
            
        if line.endswith(":"):
            label_def = line[:-1].strip()
            continue
            
        # Parse mnemonic and args
        parts = []
        in_quotes = False
        escaped = False
        current = []
        for char in line:
            if escaped:
                current.append(char)
                escaped = False
            elif char == '\\':
                escaped = True
                current.append(char)
            elif char == '"':
                in_quotes = not in_quotes
                current.append(char)
            elif char.isspace() and not in_quotes:
                if current:
                    parts.append("".join(current))
                    current = []
            else:
                current.append(char)
        if current:
            parts.append("".join(current))
            
        if not parts:
            continue
            
        mnemonic = parts[0]
        args = parts[1:]
        
        instructions.append({
            "label": label_def,
            "mnemonic": mnemonic,
            "args": args
        })
        label_def = None
        
    # Pass 1: Calculate PC values
    pc = 0
    inst_info_list = []
    label_pcs = {}
    
    for inst in instructions:
        lbl = inst["label"]
        if lbl:
            label_pcs[lbl] = pc
            
        mnemonic = inst["mnemonic"]
        raw_args = inst["args"]
        
        if mnemonic == "end":
            inst_info_list.append({"pc": pc, "code": 0, "size": 1, "data": b""})
            pc += 1
            continue
            
        if mnemonic.startswith("raw_action_0x"):
            code = int(mnemonic[13:], 16)
            # parse args as hex bytes
            act_data = bytes.fromhex("".join(raw_args))
            if code < 0x80:
                size = 1
                inst_info_list.append({"pc": pc, "code": code, "size": size, "data": b""})
            else:
                size = 3 + len(act_data)
                inst_info_list.append({"pc": pc, "code": code, "size": size, "data": act_data})
            pc += size
            continue
            
        if mnemonic not in AVM1_MNEMONICS:
            raise ValueError(f"Unknown AVM1 mnemonic: '{mnemonic}'")
            
        code = AVM1_MNEMONICS[mnemonic]
        
        if code < 0x80:
            inst_info_list.append({"pc": pc, "code": code, "size": 1, "data": b""})
            pc += 1
        else:
            # Multi-byte action size calculations
            act_data = bytearray()
            if code == 0x96:  # push
                # args are push values
                for arg in raw_args:
                    act_data.extend(serialize_push_value(arg))
            elif code in (0x99, 0x9D):  # jump, if
                # offset placeholder (2 bytes relative jump)
                act_data.extend([0, 0])
            elif code == 0x81:  # goto_frame
                frame = int(raw_args[0])
                act_data.extend(frame.to_bytes(2, "little"))
            elif code == 0x83:  # get_url
                url = raw_args[0].strip('"').encode("utf-8") + b"\x00"
                target = raw_args[1].strip('"').encode("utf-8") + b"\x00"
                act_data.extend(url + target)
            elif code == 0x87:  # store_register
                act_data.append(int(raw_args[0]))
            elif code == 0x88:  # constant_pool
                # Parse brackets e.g. ["a", "b"]
                args_joined = " ".join(raw_args)
                args_stripped = args_joined.strip("[]")
                # Split strings, keep quotes
                pool_vals = []
                in_quotes = False
                curr = []
                for char in args_stripped:
                    if char == '"':
                        in_quotes = not in_quotes
                        curr.append(char)
                    elif char == ',' and not in_quotes:
                        pool_vals.append("".join(curr).strip())
                        curr = []
                    else:
                        curr.append(char)
                if curr:
                    pool_vals.append("".join(curr).strip())
                    
                pool_strings = [p.strip('"') for p in pool_vals if p]
                act_data.extend(len(pool_strings).to_bytes(2, "little"))
                for s in pool_strings:
                    act_data.extend(s.encode("utf-8") + b"\x00")
            elif code == 0x89:  # strict_mode
                act_data.append(int(raw_args[0]))
            elif code == 0x8A:  # wait_for_frame
                frame = int(raw_args[0])
                skip = int(raw_args[1])
                act_data.extend(frame.to_bytes(2, "little"))
                act_data.append(skip)
            elif code == 0x8B:  # set_target
                target = raw_args[0].strip('"').encode("utf-8") + b"\x00"
                act_data.extend(target)
            elif code == 0x8C:  # goto_label
                label = raw_args[0].strip('"').encode("utf-8") + b"\x00"
                act_data.extend(label)
            elif code == 0x8D:  # wait_for_frame2
                act_data.append(int(raw_args[0]))
            elif code == 0x9A:  # get_url2
                act_data.append(int(raw_args[0]))
            elif code == 0x9F:  # goto_frame2
                flags = int(raw_args[0])
                bias = int(raw_args[1]) if len(raw_args) > 1 else 0
                act_data.append(flags)
                act_data.extend(bias.to_bytes(2, "little"))
                
            size = 3 + len(act_data) # 1 code + 2 length + payload
            inst_info_list.append({"pc": pc, "code": code, "size": size, "data": bytes(act_data), "label_target": raw_args[0] if code in (0x99, 0x9D) else None})
            pc += size
            
    # Pass 2: Write bytes, resolving jumps
    out = bytearray()
    for inst in inst_info_list:
        pc = inst["pc"]
        code = inst["code"]
        data = inst["data"]
        
        out.append(code)
        if code >= 0x80:
            if code in (0x99, 0x9D):
                target_label = inst["label_target"]
                if target_label not in label_pcs:
                    raise ValueError(f"Label '{target_label}' not defined")
                target_pc = label_pcs[target_label]
                # Offset is target_pc - (pc + 5)
                relative_offset = target_pc - (pc + 5)
                data = relative_offset.to_bytes(2, "little", signed=True)
                
            out.extend(len(data).to_bytes(2, "little"))
            out.extend(data)
            
    return bytes(out)
