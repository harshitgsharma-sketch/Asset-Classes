"""Does sector relative strength persist (momentum) or reverse (contrarian) in India?
Ranks 13 Nifty sector indices each month by trailing return minus Nifty 50, then
compares with the following return minus Nifty 50. Yahoo Finance monthly closes,
10 years. Run: python3 -I scripts/research/sector_momentum_test.py
Used for knowledge/board-backlog.md (week of 2026-11-22, second batch).
"""
import json, urllib.request, urllib.parse, datetime, statistics as st
UA={'User-Agent':'Mozilla/5.0'}
S={'Bank':'^NSEBANK','IT':'^CNXIT','FMCG':'^CNXFMCG','Realty':'^CNXREALTY','Energy':'^CNXENERGY','Auto':'^CNXAUTO','PSU Bank':'^CNXPSUBANK','Metal':'^CNXMETAL','Pharma':'^CNXPHARMA','Infra':'^CNXINFRA','Consumption':'^CNXCONSUM','Next 50':'^NSMIDCP','Fin Services':'NIFTY_FIN_SERVICE.NS'}
def monthly(sym):
    j=json.load(urllib.request.urlopen(urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(sym,safe='')+'?range=10y&interval=1mo',headers=UA),timeout=25))['chart']['result'][0]
    return {datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m'):c for t,c in zip(j['timestamp'],j['indicators']['quote'][0]['close']) if c}
N=monthly('^NSEI'); D={k:monthly(v) for k,v in S.items()}
months=sorted(N)
def r(s,a,b): return s[months[b]]/s[months[a]]-1
def spearman(x,y):
    rx={v:i for i,v in enumerate(sorted(x))}; ry={v:i for i,v in enumerate(sorted(y))}
    a=[rx[v] for v in x]; b=[ry[v] for v in y]; n=len(a); ma=sum(a)/n; mb=sum(b)/n
    num=sum((p-ma)*(q-mb) for p,q in zip(a,b)); den=(sum((p-ma)**2 for p in a)*sum((q-mb)**2 for q in b))**.5
    return num/den if den else 0
for L,H in [(6,1),(6,3),(6,6),(6,12),(12,12),(12,36)]:
    ics=[];spread=[]
    for t in range(L,len(months)-H):
        xs=[];ys=[]
        for k,s in D.items():
            if all(months[i] in s for i in (t-L,t,t+H)):
                xs.append(r(s,t-L,t)-r(N,t-L,t)); ys.append(r(s,t,t+H)-r(N,t,t+H))
        if len(xs)>=8:
            ics.append(spearman(xs,ys)); o=sorted(zip(xs,ys)); q=len(o)//3
            spread.append(st.mean(y for _,y in o[-q:])-st.mean(y for _,y in o[:q]))
    print(f'lookback {L}m -> next {H}m: rank corr mean {st.mean(ics):+.3f} (positive in {sum(i>0 for i in ics)/len(ics):.0%} of {len(ics)} months); top-third minus bottom-third {st.mean(spread)*100:+.1f} pp')
print('period',months[0],'to',months[-1],'sectors',len(D))
