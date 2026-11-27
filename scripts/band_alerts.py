"""Band-change alerts: compare the new data/signals.json with the last committed one.

Run by the refresh Action after the sanity check. When a reading moves into a different band,
or its parabolic flag turns on, it:
  - opens a GitHub issue in this repo (GitHub emails the repo owner about new issues), when
    GH_TOKEN and GITHUB_REPOSITORY are set (the Action sets both);
  - sends a Telegram message, when the TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets exist.
Only headline readings are checked (not the ~450 Nifty 500 stocks outside the Nifty 50 and
the watchlist). Daily price refreshes do not change scores, so alerts come after model runs.
Best effort: never fails the Action. Standard library only.
"""
import json, os, subprocess, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://harshitgsharma-sketch.github.io/Asset-Classes/'


def load_old():
    try:
        raw = subprocess.run(['git', 'show', 'HEAD:data/signals.json'], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return json.loads(raw)
    except Exception:
        return None


def headline(i):
    if i.get('model') != 'stocks':
        return True
    m = i.get('meta') or {}
    return m.get('Universe') == 'Nifty 50' or i.get('watch')


def changes(old, new):
    o = {i['id']: i for i in old.get('items', [])}
    out = []
    for i in new.get('items', []):
        if not headline(i) or i.get('score') is None:
            continue
        p = o.get(i['id'])
        if not p or p.get('score') is None:
            continue
        if p.get('band') != i.get('band'):
            out.append(f"{i['name']}: {p['band']} ({p['score']}) -> {i['band']} ({i['score']})")
        ps = (p.get('parabolic') or {}).get('status', 'Normal')
        ns = (i.get('parabolic') or {}).get('status', 'Normal')
        if ns != 'Normal' and ps == 'Normal':
            out.append(f"{i['name']}: parabolic flag on ({ns}, {round(100 * i['parabolic']['gap'])}% above the 150-day EMA)")
    return out


def github_issue(title, body):
    repo, tok = os.environ.get('GITHUB_REPOSITORY'), os.environ.get('GH_TOKEN')
    if not (repo and tok):
        return
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/issues', method='POST',
                                 data=json.dumps({'title': title, 'body': body, 'labels': ['band-alert']}).encode(),
                                 headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        print('issue opened:', json.load(r).get('html_url'))


def telegram(text):
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (tok and chat):
        return
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'disable_web_page_preview': 'true'}).encode()
    urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data=data, timeout=20)
    print('telegram sent')


def main():
    old = load_old()
    new = json.load(open(os.path.join(ROOT, 'data', 'signals.json')))
    if not old:
        print('no previous signals.json; no alerts')
        return
    ch = changes(old, new)
    if not ch:
        print('no band changes')
        return
    day = new.get('built_at', '')[:10]
    title = f"Board: {len(ch)} band change{'s' if len(ch) > 1 else ''} ({day})"
    body = '\n'.join('- ' + c for c in ch) + f'\n\n{SITE}\n\nNot investment advice.'
    print(title + '\n' + body)
    for f, args in ((github_issue, (title, body)), (telegram, (title + '\n' + body,))):
        try:
            f(*args)
        except Exception as e:
            print(f'WARN {f.__name__}: {type(e).__name__}: {e}')


if __name__ == '__main__':
    main()
