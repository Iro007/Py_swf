"""Simple name inference heuristics for ABC files.
Produces suggested readable names for multinames and strings based on frequency and context.
"""
from typing import Dict
from collections import defaultdict


def sanitize_name(s: str) -> str:
    # Keep alnum and underscore, replace others with underscore
    if not s:
        return s
    out = []
    for ch in s:
        if ch.isalnum() or ch == '_':
            out.append(ch)
        else:
            out.append('_')
    name = ''.join(out)
    # Collapse consecutive underscores
    while '__' in name:
        name = name.replace('__', '_')
    # Strip leading/trailing underscores
    name = name.strip('_')
    if not name:
        return 'n'
    return name


def infer_names(abc) -> Dict[str, Dict[int, str]]:
    """Return a mapping: {'multiname': {idx: name}, 'string': {idx: name}}
    Heuristics:
    - Collect candidate names from pool.strings
    - Count occurrences of multinames and string refs in instances, traits and methods
    - Prefer more frequent names
    """
    pool = abc.constant_pool
    multiname_counts = defaultdict(int)
    string_counts = defaultdict(int)

    # Instances
    for inst in getattr(abc, 'instances', []):
        try:
            multiname_counts[inst.name] += 3
        except Exception:
            pass
        for t in getattr(inst, 'traits', []):
            try:
                multiname_counts[t.name] += 1
            except Exception:
                pass

    # Classes and scripts traits
    for c in getattr(abc, 'classes', []):
        for t in getattr(c, 'traits', []):
            try:
                multiname_counts[t.name] += 1
            except Exception:
                pass
    for s in getattr(abc, 'scripts', []):
        for t in getattr(s, 'traits', []):
            try:
                multiname_counts[t.name] += 1
            except Exception:
                pass

    # Methods (string names)
    for mi, m in enumerate(getattr(abc, 'methods', [])):
        try:
            string_counts[m.name] += 2
        except Exception:
            pass

    # Traits top-level
    for mb in getattr(abc, 'method_bodies', []):
        for t in getattr(mb, 'traits', []):
            try:
                multiname_counts[t.name] += 1
            except Exception:
                pass

    # Build mapping from multiname index to simplified name
    multiname_map = {}
    used = set()

    # For multinames, attempt to derive from resolved multiname using pool.strings
    for idx in range(len(getattr(pool, 'multinames', []))):
        try:
            mn = pool.multinames[idx]
        except Exception:
            mn = None
        if not mn:
            continue
        # prefer name field when present
        name_part = None
        if 'name' in mn and isinstance(mn['name'], int) and mn['name'] < len(pool.strings):
            name_part = pool.strings[mn['name']]
        if not name_part:
            # fallback to namespace or placeholder
            name_part = f'prop_{idx}'
        cand = sanitize_name(name_part)
        if not cand:
            cand = f'prop_{idx}'
        base = cand
        i = 1
        while cand in used:
            cand = f"{base}_{i}"
            i += 1
        multiname_map[idx] = cand
        used.add(cand)

    # Map string indices to sanitized names (for method names)
    string_map = {}
    for si in range(len(getattr(pool, 'strings', []))):
        s = pool.strings[si]
        if not s:
            continue
        cand = sanitize_name(s)
        if not cand:
            continue
        base = cand
        i = 1
        while cand in used:
            cand = f"{base}_{i}"
            i += 1
        string_map[si] = cand
        used.add(cand)

    return {'multiname': multiname_map, 'string': string_map}
