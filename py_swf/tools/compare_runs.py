"""Run decompiler across fixtures and compare to baseline.
Usage: python py_swf/tools/compare_runs.py
Creates outputs/current and outputs/baseline; writes reports/diffs.txt
"""
import sys
from pathlib import Path
import subprocess
import difflib

ROOT = Path(__file__).resolve().parents[1]
FIX_DIR = ROOT / 'tests' / 'fixtures'
OUT_DIR = ROOT / 'outputs'
REPORTS = ROOT.parent / 'reports'

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / 'current').mkdir(parents=True, exist_ok=True)
(OUT_DIR / 'baseline').mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

py = sys.executable

def run_decompile(b64_path, out_path):
    cmd = [py, str(ROOT / 'tools' / 'decompile_abc.py'), str(b64_path)]
    p = subprocess.run(cmd, capture_output=True, timeout=30)
    if p.returncode != 0:
        return False, p.stderr.decode('utf8', errors='ignore')
    out_path.write_text(p.stdout.decode('utf8', errors='ignore'))
    return True, ''


def main():
    fixtures = sorted(FIX_DIR.glob('*.abc.b64'))
    for f in fixtures:
        name = f.stem
        cur = OUT_DIR / 'current' / (name + '.as')
        ok, err = run_decompile(f, cur)
        if not ok:
            cur.write_text('<!-- decompile failed: ' + err + ' -->')

    # compare to baseline
    diffs = []
    baseline_files = {p.stem: p for p in (OUT_DIR / 'baseline').glob('*.as')}
    for curp in sorted((OUT_DIR / 'current').glob('*.as')):
        stem = curp.stem
        basep = baseline_files.get(stem)
        curtxt = curp.read_text(errors='ignore').splitlines()
        if basep is None:
            diffs.append(f'NEW: {stem}')
            continue
        basetxt = basep.read_text(errors='ignore').splitlines()
        if curtxt != basetxt:
            d = difflib.unified_diff(basetxt, curtxt, fromfile='baseline/'+stem+'.as', tofile='current/'+stem+'.as', lineterm='')
            diffs.append('\n'.join(d))
    # write report
    rpt = REPORTS / 'compare_diffs.txt'
    if diffs:
        rpt.write_text('\n\n'.join(diffs))
    else:
        rpt.write_text('No differences found')

    # if baseline empty, bootstrap it
    if not any((OUT_DIR / 'baseline').glob('*.as')):
        # copy current to baseline
        for p in (OUT_DIR / 'current').glob('*.as'):
            (OUT_DIR / 'baseline' / p.name).write_text(p.read_text())
        print('Bootstrapped baseline from current run')
    else:
        print('Comparison complete; report at', rpt)

if __name__ == '__main__':
    main()
