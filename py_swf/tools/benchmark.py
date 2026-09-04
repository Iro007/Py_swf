"""Simple benchmark for decompilation time over fixtures.
Usage: python py_swf/tools/benchmark.py [fixtures_dir]
"""
import sys
import time
from pathlib import Path
import base64
import subprocess


def decompile_with_python(b64_path):
    cmd = [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools' / 'decompile_abc.py'), str(b64_path)]
    start = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=30)
        elapsed = time.time() - start
        return elapsed, p.returncode, p.stdout.decode('utf8', errors='ignore')[:200]
    except Exception as e:
        return None, -1, str(e)


def main():
    fixtures = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('tests/fixtures')
    if not fixtures.exists():
        print('Fixtures dir not found:', fixtures)
        return 2
    results = []
    for p in fixtures.glob('*.abc.b64'):
        print('Benchmarking', p.name)
        elapsed, ret, out = decompile_with_python(p)
        if elapsed is None:
            print('  Error:', out)
            results.append((p.name, None, ret))
        else:
            print(f'  Time: {elapsed:.3f}s, return {ret}')
            results.append((p.name, elapsed, ret))
    # Summary
    times = [r[1] for r in results if r[1] is not None]
    if times:
        import statistics
        print('\nSummary:')
        print('  count', len(times))
        print('  mean', statistics.mean(times))
        print('  stdev', statistics.pstdev(times))
    else:
        print('\nNo successful runs')
    return 0

if __name__ == '__main__':
    sys.exit(main())
