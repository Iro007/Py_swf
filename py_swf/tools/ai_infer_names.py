"""Optional AI-backed name inference.
- If DECOMPILER_SERVER env var is set, this script posts extracted strings to the server's /api/decompile-ai endpoint
  with taskType 'name_suggestion'. Otherwise it prints instructions on how to enable AI naming.
Usage: python py_swf/tools/ai_infer_names.py path/to/abc.b64
"""
import os
import sys
import json
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import py_swf.avm2 as avm2


def extract_strings(abc_bytes):
    abc = avm2.ABCFile()
    abc.parse(abc_bytes)
    pool = abc.constant_pool
    return [s for s in pool.strings if s]


def post_to_server(server_url, payload):
    import urllib.request
    req = urllib.request.Request(server_url, data=json.dumps(payload).encode('utf8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf8'))


def main():
    if len(sys.argv) < 2:
        print('Usage: ai_infer_names.py <path-to-abc-or-b64>')
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print('File not found:', path)
        return 2

    data = path.read_bytes()
    # if file looks like base64 text, decode
    try:
        if b'\n' not in data and all(32 <= b < 127 for b in data[:40]):
            # likely base64
            abc_bytes = base64.b64decode(data)
        else:
            abc_bytes = data
    except Exception:
        abc_bytes = data

    strings = extract_strings(abc_bytes)
    if not strings:
        print('No strings found in ABC payload')
        return 0

    server = os.environ.get('DECOMPILER_SERVER') or os.environ.get('DECOMPILER_API_URL') or 'http://localhost:3000/api/decompile-ai'
    payload = {
        'bytecode': '\n'.join(strings[:200]),
        'taskType': 'name_suggestion',
        'filename': path.name
    }

    if 'GEMINI_API_KEY' not in os.environ and 'DECOMPILER_SERVER' not in os.environ:
        print('AI naming is opt-in. To enable, either run a local server (the web app) or set GEMINI_API_KEY in environment.\n')
        print('Strings extracted sample (first 20):')
        for s in strings[:20]:
            print(' -', s)
        return 0

    try:
        result = post_to_server(server, payload)
        print('AI response:')
        print(json.dumps(result, indent=2)[:2000])
    except Exception as e:
        print('Failed to call server:', e)
        return 3

    return 0


if __name__ == '__main__':
    sys.exit(main())
