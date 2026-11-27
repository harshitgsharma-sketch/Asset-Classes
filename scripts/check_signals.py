"""Sanity check data/signals.json before the refresh Action commits it.

Compares the freshly built file with the last committed one (git HEAD). Exits 1, so the
Action stops before its commit step, when the new build looks broken:
  - fewer than 90% of the previous items, or a model that had readings now has none
  - a headline reading (Gold, Nifty 50, Bitcoin) is missing or unscored
  - any score outside 1-100
  - a model's inputs date went backwards
Standard library only.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(ROOT, 'data', 'signals.json')
HEADLINE = ['GOLD', 'NIFTY50', 'BTC']


def previous():
    try:
        raw = subprocess.run(['git', 'show', 'HEAD:data/signals.json'], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return json.loads(raw)
    except Exception:
        return None


def main():
    new = json.load(open(NEW))
    old = previous()
    errs = []
    items = new.get('items', [])
    ids = {i['id']: i for i in items}
    for h in HEADLINE:
        if h not in ids or ids[h].get('score') is None:
            errs.append(f'headline reading {h} is missing or unscored')
    for i in items:
        s = i.get('score')
        if s is not None and not (0 < s <= 100):
            errs.append(f"{i['id']} score {s} is outside 1-100")
    if old:
        n_old, n_new = len(old.get('items', [])), len(items)
        if n_old and n_new < 0.9 * n_old:
            errs.append(f'items fell from {n_old} to {n_new}')
        had = {i['model'] for i in old.get('items', []) if i.get('score') is not None}
        has = {i['model'] for i in items if i.get('score') is not None}
        for m in sorted(had - has):
            errs.append(f'model {m} had readings and now has none')
        for k, m in (old.get('models') or {}).items():
            a, b = m.get('asof'), (new.get('models') or {}).get(k, {}).get('asof')
            if a and b and b < a:
                errs.append(f'model {k} inputs date went back from {a} to {b}')
    if errs:
        print('signals.json failed the sanity check; not publishing:')
        for e in errs:
            print('  -', e)
        sys.exit(1)
    print(f'signals.json passed the sanity check ({len(items)} items)')


if __name__ == '__main__':
    main()
