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


def _best_segment(s: str) -> str:
    # If the string looks like dotted path, prefer the last segment
    if not s:
        return ''
    if '.' in s:
        seg = s.split('.')[-1]
        if seg:
            return seg
    # prefer camelCase or underscore segments
    for sep in ['/', '\\', '_', '-', ' ']:
        if sep in s:
            parts = [p for p in s.split(sep) if p]
            if parts:
                return parts[-1]
    return s


def infer_names(abc) -> Dict[str, Dict[int, str]]:
    """Return a mapping: {'multiname': {idx: name}, 'string': {idx: name}}
    Heuristics:
    - Collect candidate names from pool.strings
    - Count occurrences of multinames and string refs in instances, traits and methods
    - Prefer more frequent names and cleaner segments (last path segment)
    - Disambiguate conflicts and avoid reserved words
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

    # Augment counts from raw pool strings frequency
    for si, s in enumerate(getattr(pool, 'strings', [])):
        if s:
            # weight frequently used strings higher
            string_counts[si] += s.count('/') + s.count('.')

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
            raw = pool.strings[mn['name']]
            name_part = _best_segment(raw)
        if not name_part:
            # fallback to namespace or placeholder
            name_part = f'prop_{idx}'
        cand = sanitize_name(name_part)
        if not cand:
            cand = f'prop_{idx}'
        # prefer more frequent multinames by appending count hint when ambiguous
        score = multiname_counts.get(idx, 0)
        base = cand
        if score > 1:
            cand = f"{base}_{score}"
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
        raw = _best_segment(s)
        cand = sanitize_name(raw)
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
