"""Monthly summary note: a one-page, plain-words read of the board after each model run.

Writes knowledge/monthly-summary-YYYY-MM.md (YYYY-MM = the month of the latest Gold & Nifty 50
model run) and lists it in knowledge/index.json, so it shows in the site's Knowledge tab. The
note uses only monthly readings (no daily prices), so it changes when a model run changes it,
not every day. When a month's note is written for the first time, it is also sent the same way
as the band alerts: a GitHub issue (emailed to the repo owner) and Telegram if configured.
Standard library only.
"""
import json, os, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KN = os.path.join(ROOT, 'knowledge')
SITE = 'https://harshitgsharma-sketch.github.io/Asset-Classes/'
BANDS = ['Strong buy', 'Buy', 'Accumulate', 'Hold', 'Trim', 'Exit']
TAB = {'core': 'Indian equities', 'sectors': 'Indian equities', 'factors': 'Indian equities', 'stocks': 'Indian equities',
       'global': 'International', 'commodities': 'Commodities', 'crypto': 'Crypto', 'bonds': 'Fixed income',
       'carry': 'Fixed income', 'reits': 'Real estate', 'property': 'Real estate'}


def mood_word(s):
    return 'fearful' if s < 35 else 'cautious' if s < 50 else 'confident' if s < 65 else 'greedy'


def headline(i):
    return i.get('score') is not None and (i['model'] != 'stocks' or (i.get('meta') or {}).get('Universe') == 'Nifty 50' or i.get('watch'))


def tab(i):
    return 'Commodities' if i['id'] == 'GOLD' else TAB.get(i['model'], '')


def build(d):
    core = (d.get('models') or {}).get('core', {}).get('asof')
    if not core:
        return None, None
    month = core[:7]
    label = datetime.date(int(month[:4]), int(month[5:]), 1).strftime('%B %Y')
    items = [i for i in d['items'] if headline(i)]
    broad = [i for i in items if i['model'] != 'stocks']
    moved = sorted([i for i in items if i.get('prev') and i['prev'].get('band') != i.get('band')],
                   key=lambda i: -abs(i['score'] - i['prev']['score']))
    cheap = sorted([i for i in broad if i['score'] <= 35 and 'not investable' not in (i.get('action') or '').lower()], key=lambda i: i['score'])
    rich = sorted([i for i in broad if i['score'] > 65], key=lambda i: -i['score'])
    stage = [i for i in cheap if not any(w in (i.get('action') or '').lower() for w in ('park new money', 'buy floating')) and (((i.get('buckets') or {}).get('Timing') or 0) > 55 or ((i.get('buckets') or {}).get('Filter') or 0) > 65
             or any(w in (i.get('action') or '').lower() for w in ('tranche', 'stage', 'thirds')))]
    acs = [a for a in d.get('assetClasses', []) if a.get('score') is not None]
    gaps = sorted([a for a in acs if a.get('own') is not None and abs(a['own'] - a['score']) >= 10], key=lambda a: -abs(a['own'] - a['score']))
    mood = (d.get('mood') or {}).get('now')
    L = [f'# Monthly summary: {label}', '',
         f'Written by the board from the {core} model run. Not investment advice: the anchors are judgment-based, and the only back-tests are the in-sample checks on the Snapshot tab. [Open the board]({SITE})', '']
    L += ['## In one line', '']
    one = []
    if mood:
        one.append(f"market mood **{mood['score']:.0f}/100 ({mood_word(mood['score'])})**")
    one.append(f"**{len(moved)}** reading{'s' if len(moved) != 1 else ''} changed band")
    one.append(f"**{len(cheap)}** in Buy or Strong buy, **{len(rich)}** in Trim or Exit (indices, commodities, crypto, bonds and real estate)")
    L += ['This month: ' + '; '.join(one) + '.', '']
    tilt = lambda s: [a['name'].split(' (')[0] for a in acs if str(a.get('tilt', '')).startswith(s)]
    if acs:
        L += ['## Asset classes', '',
              f"- **Add:** {', '.join(tilt('Overweight')) or 'none'}",
              f"- **Trim:** {', '.join(tilt('Underweight')) or 'none'}",
              f"- **Neutral:** {len(acs) - len(tilt('Overweight')) - len(tilt('Underweight'))} others", '']
    L += ['## What changed band since the last run', '']
    if moved:
        L += ['| Reading | Area | Was | Now |', '|---|---|---|---|']
        L += [f"| {i['name']} | {tab(i)} | {i['prev']['band']} ({i['prev']['score']}) | **{i['band']}** ({i['score']}) |" for i in moved[:15]]
        if len(moved) > 15:
            L.append(f'\n…and {len(moved) - 15} more on the Snapshot tab.')
    else:
        L.append('Nothing changed band.')
    L += ['']
    def lst(title, rows, note=''):
        out = [f'## {title}', '']
        if not rows:
            return out + ['None this month.', '']
        out += [f"- **{i['name']}** ({tab(i)}): {i['score']}, {i['band']}" + (f" · {i['action']}" if i.get('action') else '') for i in rows[:10]]
        return out + ([f'\n{note}'] if note else []) + ['']
    L += lst('Cheapest readings (score 35 or lower)', cheap)
    L += lst('Buy in stages rather than at once', stage, 'Cheap, but timing or the macro filter argues against a lump sum.')
    L += lst('Richest readings (above 65): trim if you hold them', rich)
    if gaps:
        L += ['## Where value and timing disagree', '',
              'The asset-class model looks at valuation only; the full model adds timing and macro.', '',
              '| Asset class | Valuation only | Full model |', '|---|---|---|']
        L += [f"| {a['name'].split(' (')[0]} | {a['score']:.0f} | {a['own']:.0f} |" for a in gaps[:8]] + ['']
    tr = d.get('track') or {}
    if tr.get('rows'):
        L += ['## Live track record', '',
              f"{len(tr['rows'])} scores have been recorded live since {tr.get('first')} (the rest of the history was reconstructed). "
              'Their results so far are on the Snapshot tab; the first 12-month results arrive a year after the first live month.', '']
    L += ['## Your portfolio', '', f'Holdings are kept in your browser only, so this note cannot see them. [Open My portfolio]({SITE}#portfolio) to see which of yours moved, and any staged-entry tranches that are due.', '']
    return month, '\n'.join(L)


def main():
    d = json.load(open(os.path.join(ROOT, 'data', 'signals.json')))
    month, text = build(d)
    if not month:
        print('monthly summary: no core model date'); return
    fn = f'monthly-summary-{month}.md'; path = os.path.join(KN, fn)
    new = not os.path.exists(path)
    if not new and open(path, encoding='utf-8').read() == text:
        print('monthly summary: unchanged'); return
    open(path, 'w', encoding='utf-8').write(text)
    ip = os.path.join(KN, 'index.json'); idx = json.load(open(ip, encoding='utf-8'))
    slug = fn[:-3]
    title = text.splitlines()[0].lstrip('# ')
    entry = {'slug': slug, 'title': title, 'file': fn, 'source': 'Board, generated', 'source_url': '',
             'added': d['models']['core']['asof'], 'tags': ['monthly', 'summary'], 'pinned': False}
    idx['notes'] = [n for n in idx['notes'] if n.get('slug') != slug] + [entry]
    open(ip, 'w', encoding='utf-8').write(json.dumps(idx, indent=2, ensure_ascii=False) + '\n')
    print(f'monthly summary: {"wrote" if new else "updated"} {fn}')
    if new:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import band_alerts
        body = text + f'\n\n{SITE}#knowledge/{slug}'
        for f, args in ((band_alerts.github_issue, (title, body)), (band_alerts.telegram, (title + '\n' + SITE + '#knowledge/' + slug,))):
            try:
                f(*args)
            except Exception as e:
                print(f'WARN {f.__name__}: {type(e).__name__}: {e}')


if __name__ == '__main__':
    main()
