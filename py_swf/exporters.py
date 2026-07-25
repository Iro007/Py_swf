from pathlib import Path

from .avm1 import disassemble_avm1
from .avm2 import ABCFile, disassemble_instructions
from .swf_parser import SWFTag


def export_scripts(swf, output_dir):
    """Export ActionScript content from a SWF into separate files.

    This is a lightweight JPEXS-inspired feature: it creates a small
    folder with one script file per AVM1/AVM2 tag and a summary index.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported_files = []
    summary_lines = ["Script export summary", "====================", ""]

    for idx, tag in enumerate(swf.tags):
        if tag.tag_type in (12, 59):
            actions_data = tag.data[2:] if tag.tag_type == 59 else tag.data
            assembly_text = disassemble_avm1(actions_data)
            filename = output_path / f"tag_{idx:03d}.avm1.as"
            filename.write_text(assembly_text, encoding="utf-8")
            exported_files.append(filename)
            summary_lines.append(f"[{idx:03d}] AVM1: {filename.name}")

        elif tag.tag_type == 82:
            parsed = tag.parse_doabc()
            if not parsed:
                continue
            _, abc_name, abc_data = parsed
            if not abc_data:
                continue

            abc = ABCFile()
            abc.parse(abc_data)
            for mb_idx, method_body in enumerate(abc.method_bodies):
                method_name = f"method_{mb_idx}"
                assembly_text = disassemble_instructions(abc.constant_pool, method_body.code)
                filename = output_path / f"tag_{idx:03d}_method_{mb_idx:02d}.avm2.as"
                filename.write_text(
                    f"# ABC: {abc_name or 'anonymous'}\n# Method index: {mb_idx}\n\n{assembly_text}",
                    encoding="utf-8",
                )
                exported_files.append(filename)
                summary_lines.append(f"[{idx:03d}] AVM2: {filename.name}")

    index_file = output_path / "script_index.txt"
    index_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    exported_files.append(index_file)
    return exported_files
