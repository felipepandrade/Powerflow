import re
import sys
from pathlib import Path

def fix_unused_ignores(mypy_output: str):
    lines_to_fix = []
    for line in mypy_output.splitlines():
        if "Unused \"type: ignore\" comment" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                file_path = parts[0].strip()
                line_num = int(parts[1].strip())
                lines_to_fix.append((file_path, line_num))
    
    # Agrupar por arquivo
    files = {}
    for f, l in lines_to_fix:
        files.setdefault(f, []).append(l)
        
    for file_path, line_nums in files.items():
        p = Path(file_path)
        if not p.exists(): continue
        lines = p.read_text("utf-8").splitlines()
        for l in sorted(line_nums, reverse=True):
            idx = l - 1
            if 0 <= idx < len(lines):
                # Remover type ignore da linha
                lines[idx] = re.sub(r'# type: ignore.*', '', lines[idx]).rstrip()
        p.write_text("\n".join(lines) + "\n", "utf-8")

mypy_out = """
src/taskflow/application/use_cases/triage_proposal.py:76: error: Incompatible types in assignment (expression has type "Any | None", variable has type "Task")  [assignment]
src/taskflow\application\use_cases\triage_proposal.py:88: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\triage_proposal.py:107: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\triage_proposal.py:124: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\triage_proposal.py:125: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\triage_proposal.py:202: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\suggest_follow_up.py:39: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\suggest_follow_up.py:40: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\suggest_follow_up.py:41: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\suggest_follow_up.py:42: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\suggest_follow_up.py:53: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\scan_stale_items.py:139: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\manage_task.py:210: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:189: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:190: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:224: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:238: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:359: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:360: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:364: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:366: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:367: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:371: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:373: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\correlate_signal.py:418: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\ingest_source_item.py:67: error: Unused "type: ignore" comment  [unused-ignore]
src/taskflow\application\use_cases\ingest_source_item.py:82: error: Unused "type: ignore" comment  [unused-ignore]
"""
fix_unused_ignores(mypy_out)
print("Done fixing ignores")
