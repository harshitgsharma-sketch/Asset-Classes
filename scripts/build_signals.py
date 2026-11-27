import pandas as pd, json, math, csv
import os,re,datetime
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M=os.path.join(ROOT,'models')+'/'
P=C=M
def band(s):
    if s is None or (isinstance(s,float) and math.isnan(s)): return None
    return 'Strong buy' if s<=20 else 'Buy' if s<=35 else 'Accumulate' if s<=50 else 'Hold' if s<=65 else 'Trim' if s<=80 else 'Exit'
def num(x):
    try:
        x=float(x); return None if math.isnan(x) else round(x,1)
    except: return None
def cov(x):
    if isinstance(x,str) and '/' in x:
        a,b=x.split('/'); return round(int(a)/int(b),2)
    return num(x)
items=[]
def add(**k):
    k['band']=band(k['score']); items.append(k)
def hist(df,col='oscillator'):
    return [[m,num(v)] for m,v in zip(df.month,df[col])]
def livem(df):
    """Months scored live (not reconstructed after the fact): the honest track record."""
    if 'source' not in df: return []
    return [m for m,src in zip(df.month,df['source']) if isinstance(src,str) and src.strip() and 'reconstructed' not in src.lower()]
def pxh(df,col):
    """Monthly price next to the score history (same months), for the price overlay and the back-test."""
    return [[m,(None if pd.isna(v) else float(v))] for m,v in zip(df.month,pd.to_numeric(df[col],errors='coerce'))]
def tier(h,c):
    if h>12: return 'A'
    return 'B' if (c is not None and c>=0.8) else 'C'
# core: gold, nifty
for key,f,nm,pc in [('GOLD','gold-score-log.csv','Gold','gold_usd'),('NIFTY50','nifty-score-log.csv','Nifty 50','nifty')]:
    d=pd.read_csv(C+f); r=d.iloc[-1]; h=hist(d)
    add(px_hist=pxh(d,pc),live_months=livem(d),id=key,name=nm,model='core',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=h,coverage=num(r.coverage),tier='A',action=None,meta={'Source':r.source},flags='History before Nov-2026 reconstructed (±3 pts)')
# sectors
d=pd.read_csv(C+'nifty-sectors-score-log.csv')
for _,r in d.iterrows():
    add(id='SEC_'+r['index'],name=r['name'],model='sectors',score=num(r.absolute),signal=r.signal,buckets={'Valuation':num(r.valuation),'Sector cycle':num(r.sector_cycle),'Timing':num(r.timing),'Filter':num(r['filter']),'Relative vs Nifty':num(r.relative)},history=[],coverage=num(r.coverage),tier='B' if r.coverage>=0.8 else 'C',action=r.quadrant,meta={'PE':num(r.pe),'Core indicators':r.core_of_17+' (v1)'},flags=r['flags'] if isinstance(r['flags'],str) else '')
# factors
d=pd.read_csv(P+'nifty-factors-score-log.csv')
for _,r in d.iterrows():
    add(id='FAC_'+r['index'],name=r['name'],model='factors',score=num(r.absolute),signal=r.signal,buckets={'Valuation':num(r.valuation),'Factor cycle':num(r.factor_cycle),'Timing':num(r.timing),'Filter':num(r['filter']),'Relative vs Nifty':num(r.relative)},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.quadrant,meta={'PE':num(r.pe),'Indicators':r.indicators},flags=r['flags'] if isinstance(r['flags'],str) else '')
# stocks
d=pd.read_csv(P+'nifty500-stocks-score-log.csv')
import json as _j
N50={x['ticker'] for x in _j.load(open(P+'nifty500-stocks-config.json'))['stocks']}
d=d[d.month==d.month.max()]
# growth and price-return inputs for the 5-year deep-value view (display only)
_inp=pd.read_csv(P+'nifty500-stocks-inputs-monthly.csv',dtype={'month':str})
_inp=_inp[_inp.month==_inp.month.max()].set_index('ticker')
_wl=os.path.join(P,'stock-watchlist.csv')
WATCH={x['Symbol'] for x in csv.DictReader(open(_wl,encoding='utf-8-sig'))} if os.path.exists(_wl) else set()
_c500=os.path.join(P,'nifty500-constituents.csv')
# NSE industry for every stock, so Nifty 50 names (hand-labelled sectors) group with the rest
IND={x['Symbol']:x['Industry'] for x in csv.DictReader(open(_c500,encoding='utf-8-sig'))} if os.path.exists(_c500) else {}
C500=set(IND)
if os.path.exists(_wl): IND.update({x['Symbol']:x['Industry'] for x in csv.DictReader(open(_wl,encoding='utf-8-sig')) if x['Symbol'] not in IND})
def growth(t):
    if t not in _inp.index: return None
    r=_inp.loc[t]
    if isinstance(r,pd.DataFrame): r=r.iloc[-1]
    eps=[float(x) for x in str(r.get('eps_hist','')).split() if x not in ('','nan')]
    return {'pg5':num(r.get('pg5')),'pg_ttm':num(r.get('pg_ttm')),'roe':num(r.get('roe')),'roe5':num(r.get('roe5')),
            'px1':num(r.get('px1')),'px3':num(r.get('px3')),'px5':num(r.get('px5')),'eps':eps,
            'eps_cagr':round(((eps[-1]/eps[0])**(1/(len(eps)-1))-1)*100,1) if len(eps)>=2 and eps[0]>0 and eps[-1]>0 else None}
for _,r in d.iterrows():
    c=cov(r.coverage)
    add(id='STK_'+r.ticker,name=r['name'],model='stocks',score=num(r.score) if 'NOT RATED' not in r.signal else None,signal=r.signal,buckets={'Valuation':num(r.valuation),'Quality':num(r.quality),'Momentum':num(r.momentum)},history=[],coverage=c,tier=tier(1,c),action=None,meta={'Ticker':r.ticker,'Universe':'Nifty 50' if r.ticker in N50 else ('Watchlist' if r.ticker in WATCH and C500 and r.ticker not in C500 else 'Nifty 500'),'Sector':r.sector,'Industry':IND.get(r.ticker,r.sector),'PE':num(r.pe),'Sector PE':num(r.sector_pe)},sidx=r.sector_index,flags=r['flags'] if isinstance(r['flags'],str) else '',growth=growth(r.ticker),watch=r.ticker in WATCH)
# global
d=pd.read_csv(C+'global-indices-score-log.csv')
for _,r in d.iterrows():
    nm=r['name'] if r['index']!='NIFTY50' else 'Nifty 50 (global 5-yr lens)'
    add(id='GLB_'+r['index'],name=f"{nm}" ,model='global',score=num(r.five_yr),signal=r.signal,buckets={'Valuation':num(r.valuation),'Macro':num(r.macro),'Currency':num(r.currency),'Timing':num(r.timing),'Filter':num(r['filter'])},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.entry_plan,meta={'Economy':r.economy,'Exp. INR return % p.a. (net)':num(r.exp_inr_net),'Range':r.exp_inr_range if isinstance(r.exp_inr_range,str) else None,'Access':r.access},flags=r['flags'] if isinstance(r['flags'],str) else '')
# commodities
d=pd.read_csv(P+'commodities-score-log.csv')
_ccfg={c['key']:c for c in json.load(open(P+'commodities-config.json'))['commodities']}
for c,nm in [('SILVER','Silver'),('BRENT','Brent crude'),('COPPER','Copper'),('ALUMINIUM','Aluminium'),('ZINC','Zinc'),('IRONORE','Iron ore'),('NATGAS','Natural gas')]:
    s=d[d.commodity==c]
    if not len(s): continue
    r=s.iloc[-1]; h=hist(s)
    add(px_hist=pxh(s,'price_usd') if len(h)>1 else [],live_months=livem(s),id='CMD_'+c,name=nm,model='commodities',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=h if len(h)>1 else [],coverage=num(r.coverage),tier=tier(len(h),num(r.coverage)),action=None,meta={'Price (USD)':num(r.price_usd),'Unit':_ccfg.get(c,{}).get('unit'),'As of':r.month,'Linked to':_ccfg.get(c,{}).get('ties'),'Indicators live':r.live},flags=('Price history: World Bank monthly averages, current month from Yahoo where it trades daily' if _ccfg.get(c,{}).get('history') else ('Month in progress; history reconstructed' if len(h)>1 else 'Only one month of history')))
# btc
d=pd.read_csv(P+'btc-score-log.csv'); r=d.iloc[-1]
add(px_hist=pxh(d,'btc_usd'),live_months=livem(d),id='BTC',name='Bitcoin',model='crypto',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=hist(d),coverage=num(r.coverage),tier='A',action='Stage entries; cap at 5% of portfolio; 31.2% VDA tax, no loss set-off',meta={'Price (₹ lakh)':num(r.btc_inr_lakh)},flags='History reconstructed; macro filter high (79)')
# top coins after Bitcoin (altcoin_oscillator.py): indicative, price-and-cycle only
if os.path.exists(P+'altcoin-score-log.csv'):
    d=pd.read_csv(P+'altcoin-score-log.csv')
    for c in ['ETH','XRP','BNB','SOL']:
        s_=d[d.coin==c]
        if not len(s_): continue
        r=s_.iloc[-1]
        add(px_hist=pxh(s_,'price_usd'),id='CRY_'+c,name=r['name'],model='crypto',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=hist(s_),coverage=num(r.coverage),tier='C',action='Indicative only; stage entries and keep all crypto within the 5% cap; 31.2% VDA tax, no loss set-off',meta={'Price (USD)':num(r.price_usd),'Indicators live':r.live},flags='Price-and-cycle model (no on-chain data); macro filter imported from the Bitcoin model')
# fixed income
d=pd.read_csv(P+'fixed-income-score-log.csv')
for _,r in d.iterrows():
    add(id='FI_'+r.instrument,name=r['name'],model='bonds',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.action,meta={'Yield %':num(r.yield_pct),'Access':r.access},flags='')
# carry
d=pd.read_csv(P+'carry-score-log.csv')
for _,r in d.iterrows():
    add(id='CRY_'+r.strategy,name=r['name'],model='carry',score=num(r.oscillator),signal=r.signal,buckets={},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.action,meta={'Post-tax yield %':num(r.post_tax_yield_pct),'Edge vs liquid (pp)':num(r.edge_vs_liquid_post_tax_pp),'Tax scenario':r.tax_scenario},flags='Realised vol and dividend yield estimated')
# reits
d=pd.read_csv(P+'real-assets-score-log.csv')
for _,r in d.iterrows():
    c=cov(r.indicators_live)
    add(id='RE_'+r.key,name=r['name'],model='reits',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Filter':num(r['filter']),'Timing':num(r.timing)},history=[],coverage=c,tier=tier(1,c),action=None,meta={'Type':r.family,'Distribution yield %':num(r.dist_yield_pct),'Spread vs G-sec (pp)':num(r.spread_vs_gsec_pp),'Price/NAV':num(r.price_to_nav),'Post-tax yield %':num(r.post_tax_yield_pct)},flags=r['flags'] if isinstance(r['flags'],str) else '')
# cities
d=pd.read_csv(P+'real-assets-city-log.csv')
for _,r in d.iterrows():
    add(id='CITY_'+r.city,name=r.city+' housing',model='property',score=num(r.valuation_score),signal=r.valuation_read,buckets={},history=[],coverage=None,tier='C',action='Valuation only: check the rent-vs-buy calculator on your own numbers',meta={'Rent yield %':num(r.rent_yield_pct),'Price CAGR 2019-26 %':num(r.price_cagr_2019_26_pct),'Source':r.source},flags='Valuation only, no timing; city indices lag')
# asset classes
d=pd.read_csv(C+'asset-classes-score-log.csv')
ac=[dict(id=r.asset,name=r['name'],family=r.family,score=num(r.valuation_score),read=r.valuation_read,tilt=r.tilt,own=num(r.own_model_oscillator),yield_=num(r.income_yield_pct),drivers=r.drivers,access=r.access) for _,r in d.iterrows()]
for a in ac: a['band']=band(a['score'])

# ---- freshness metadata: latest date mentioned in each model's log 'source' text, else month end
MON={m:i for i,m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'],1)}
def latest_date(path,month_col='month'):
    d=pd.read_csv(M+path); txt=' '.join(str(x) for x in d.astype(str).values.ravel())
    best=None
    for dd,mm,yy in re.findall(r'(\d{1,2})[- ]([A-Za-z]{3})[a-z]*[- ](\d{2,4})',txt):
        if mm.lower() not in MON: continue
        y=int(yy); y=y+2000 if y<100 else y
        try: dt=datetime.date(y,MON[mm.lower()],int(dd))
        except ValueError: continue
        if dt<=datetime.date.today() and (best is None or dt>best): best=dt
    if best is None and month_col in d:
        y,m=map(int,str(d[month_col].max()).split('-')); best=datetime.date(y,m,1)  # conservative: start of the scored month
    return best.isoformat() if best else None
MODELS={ # key: (log file, expected refresh cadence in days, how it is refreshed)
 'core':('nifty-score-log.csv',35,'monthly Claude run (3rd)'),
 'sectors':('nifty-sectors-score-log.csv',35,'monthly Claude run (3rd)'),
 'factors':('nifty-factors-score-log.csv',35,'monthly Claude run (3rd)'),
 'stocks':('nifty500-stocks-score-log.csv',35,'monthly Claude run (3rd)'),
 'global':('global-indices-score-log.csv',35,'monthly Claude run (3rd)'),
 'commodities':('commodities-score-log.csv',35,'monthly Claude run (3rd)'),
 'crypto':('btc-score-log.csv',35,'monthly Claude run (3rd)'),
 'bonds':('fixed-income-score-log.csv',35,'monthly Claude run (3rd)'),
 'carry':('carry-score-log.csv',35,'monthly Claude run (3rd)'),
 'reits':('real-assets-score-log.csv',35,'monthly Claude run (3rd)'),
 'property':('real-assets-city-log.csv',100,'quarterly (housing data is quarterly)'),
}
meta={k:{'asof':latest_date(f,'month' if k!='property' else 'x'),'cadence_days':c,'refresh':h} for k,(f,c,h) in MODELS.items()}
if meta['property']['asof'] is None: meta['property']['asof']=meta['reits']['asof']
# prices used by the last scoring run (for drift vs live prices on the page)
def last(path,col):
    d=pd.read_csv(M+path); return num(d[col].iloc[-1])
cm=pd.read_csv(M+'commodities-inputs-monthly.csv').iloc[-1]
run_prices={'gold_usd':last('gold-inputs-monthly.csv','gold_usd'),'silver_usd':num(cm.silver_usd),'brent_usd':num(cm.brent_usd),
 'copper_usd_t':num(cm.copper_usd_t),'btc_usd':last('btc-inputs-monthly.csv','btc_usd'),'usdinr':last('gold-inputs-monthly.csv','usdinr'),
 'nifty':last('nifty-inputs-monthly.csv','nifty')}
prices=None
pp=os.path.join(ROOT,'data','prices.json')
if os.path.exists(pp):
    try: prices=json.load(open(pp))
    except Exception: prices=None
# parabolic-move flag (scripts/fetch_parabolic.py): shown on the board, never changes a score
parabolic=None
pq=os.path.join(ROOT,'data','parabolic.json')
if os.path.exists(pq):
    try:
        pj=json.load(open(pq))
        for it in items:
            p=pj['items'].get(it['id'])
            if p and 'gap' in p:
                eps=p.get('episodes',[])
                it['parabolic']={'gap':p['gap'],'status':p['status'],'asof':p['asof'],'max_gap_1y':p['max_gap_1y'],
                    'from':p.get('history_from'),'episodes':len(eps),'last_episode':eps[-1] if eps else None,
                    'stale':bool(p.get('note'))}
                if p.get('drawdown'): it['drawdown']=dict(p['drawdown'],asof=p['asof'],stale=bool(p.get('note')))
                if p.get('setup'): it['setup']=dict(p['setup'],asof=p['asof'],stale=bool(p.get('note')))
        parabolic={'built_at':pj['built_at'],'rule':pj['rule'],'summary':pj['summary'],'setup_rule':pj.get('setup_rule')}
    except Exception as e:
        print('WARN parabolic.json unreadable:',e)
# thematic-fund froth (sectors model S4): latest reading + history for the board
amfi=None
aq=os.path.join(M,'amfi-thematic-monthly.csv')
if os.path.exists(aq):
    try:
        import sys; sys.path.insert(0,M)
        cwd=os.getcwd(); os.chdir(M)
        import sector_oscillator as so
        fr=so.amfi_froth(); os.chdir(cwd)
        ad=pd.read_csv(aq,dtype={'month':str})
        last=ad.iloc[-1]
        amfi={'month':last.month,'froth':fr.get(last.month),'history':[[m,fr[m]] for m in sorted(fr)],
              'them_net_cr':float(last.them_net_cr),'flow_3m_pct_aum':float(last.flow_3m_pct_aum),'share_3m':float(last.share_3m),
              'new_schemes_6m':int(last.new_schemes_6m),'aum_share':float(last.aum_share),
              'peak':(lambda r:[r.month,fr.get(r.month)])(ad.loc[ad.flow_3m_pct_aum.idxmax()]),
              'applies_to':['SEC_NEXT50','SEC_MIDSELECT','SEC_MIDCAP150','SEC_SMALLCAP250','SEC_NIFTY500','SEC_CPSE','SEC_DEFENCE','SEC_INFRA']}
    except Exception as e:
        print('WARN amfi froth:',e)
watchlist=[{'ticker':x['Symbol'],'name':x['Company Name'],'industry':x['Industry']} for x in csv.DictReader(open(_wl,encoding='utf-8-sig'))] if os.path.exists(_wl) else []
# market-cap rotation (scripts/size_rotation.py): Indian equities "Market cap" view, never changes a score
size_rotation=None
sq=os.path.join(ROOT,'data','size_rotation.json')
if os.path.exists(sq):
    try: size_rotation=json.load(open(sq))
    except Exception as e: print('WARN size_rotation.json unreadable:',e)
# ---- band back-test (display only): forward price return after each month, grouped by that month's band.
# Uses the 61-month score histories, most of them reconstructed, so it is a sanity check, not proof.
BANDS=['Strong buy','Buy','Accumulate','Hold','Trim','Exit']
def backtest(horizons=(12,24)):
    obs={H:[] for H in horizons}
    for it in items:
        h=it.get('history') or []; px=dict(it.get('px_hist') or [])
        if len(h)<13 or not px: continue
        months=[m for m,_ in h]
        for k,(m,sc) in enumerate(h):
            if sc is None or not px.get(m): continue
            for H in horizons:
                if k+H<len(months) and px.get(months[k+H]):
                    obs[H].append((band(sc),px[months[k+H]]/px[m]-1,it['id']))
    def summ(rows):
        out=[]
        for b in BANDS:
            r=sorted(x[1] for x in rows if x[0]==b); n=len(r)
            if not n: out.append({'band':b,'n':0}); continue
            med=r[n//2] if n%2 else (r[n//2-1]+r[n//2])/2
            out.append({'band':b,'n':n,'assets':len({x[2] for x in rows if x[0]==b}),'median':round(med,4),
                        'hit':round(sum(1 for x in r if x>0)/n,3),'p25':round(r[int(n*.25)],4),'p75':round(r[min(n-1,int(n*.75))],4)})
        return out
    ids=sorted({x[2] for H in horizons for x in obs[H]})
    ms=[m for it in items if it['id'] in ids for m,_ in it['history']]
    return {'horizons':list(horizons),'n':{str(H):len(obs[H]) for H in horizons},'assets':ids,
            'from':min(ms) if ms else None,'to':max(ms) if ms else None,
            'by_band':{str(H):summ(obs[H]) for H in horizons},
            'per_asset':{i:{str(H):summ([x for x in obs[H] if x[2]==i]) for H in horizons} for i in ids}}
bt=backtest()

# ---- score snapshots per model run, so the board can show what changed since the previous run.
# data/score-snapshots.json: {model: {asof: {id: score}}}; the current run overwrites its own key.
snp=os.path.join(ROOT,'data','score-snapshots.json')
try: snaps=json.load(open(snp))
except Exception: snaps={}
for k,m in meta.items():
    if not m['asof']: continue
    snaps.setdefault(k,{})[m['asof']]={it['id']:it['score'] for it in items if it['model']==k and it['score'] is not None}
    snaps[k]={a:snaps[k][a] for a in sorted(snaps[k])[-24:]}
for it in items:
    k=it['model']; cur=meta.get(k,{}).get('asof'); prev=None
    older=[a for a in sorted(snaps.get(k,{})) if cur and a<cur]
    if older and it['id'] in snaps[k][older[-1]]:
        prev={'score':snaps[k][older[-1]][it['id']],'asof':older[-1],'source':'previous run'}
    elif it.get('history') and len(it['history'])>1 and it['history'][-2][1] is not None:
        prev={'score':it['history'][-2][1],'asof':it['history'][-2][0],'source':'score history'}
    if prev: prev['band']=band(prev['score']); it['prev']=prev
os.makedirs(os.path.join(ROOT,'data'),exist_ok=True)
json.dump(snaps,open(snp,'w'),separators=(',',':'))

# ---- provisional scores at today's prices (scripts/provisional_scores.py): display only
provisional=None
try:
    provisional=json.load(open(os.path.join(ROOT,'data','provisional.json')))
    for it in items:
        p=provisional['items'].get(it['id'])
        if p: it['provisional']=dict(p,band=band(p['score']),at=provisional.get('prices_at'))
except Exception as e: print('WARN provisional.json:',e)

# ---- live track record: months scored at the time (not reconstructed), and the price change since
LIVEKEY={'GOLD':'gold_usd','NIFTY50':'nifty','BTC':'btc_usd','CMD_SILVER':'silver_usd','CMD_BRENT':'brent_usd','CMD_COPPER':'copper_usd_t'}
pv=(prices or {}).get('values',{})
track_rows=[]
for it in items:
    px=dict(it.get('px_hist') or []); hs=dict(it.get('history') or [])
    for m in it.get('live_months') or []:
        p0=px.get(m); sc=hs.get(m)
        if not p0 or sc is None: continue
        k=LIVEKEY.get(it['id']); p1=pv.get(k,{}).get('value') if k else None
        later=[(mm,v) for mm,v in it['px_hist'] if mm>m and v]
        if p1 is None and later: p1=later[-1][1]
        if not p1: continue
        track_rows.append({'id':it['id'],'name':it['name'],'month':m,'score':sc,'band':band(sc),'px0':p0,'px1':p1,'ret':round(p1/p0-1,4)})
track={'rows':sorted(track_rows,key=lambda r:(r['month'],r['score'])),'first':min([r['month'] for r in track_rows],default=None)}
track['by_band']=[{'band':b,'n':len(r),'median':(round(sorted(r)[len(r)//2] if len(r)%2 else (sorted(r)[len(r)//2-1]+sorted(r)[len(r)//2])/2,4) if r else None)}
                  for b in BANDS for r in [[x['ret'] for x in track_rows if x['band']==b]]]

# ---- price-proxy back-test for sectors and global (scripts/proxy_backtest.py via fetch_parabolic.py)
proxy=None
try: proxy=json.load(open(os.path.join(ROOT,'data','proxy_backtest.json')))
except Exception as e: print('WARN proxy_backtest.json:',e)

# ---- market mood: 0 fearful .. 100 greedy, monthly since the score histories start
def mood():
    nv=pd.read_csv(C+'nifty-score-log.csv'); nval=dict(zip(nv.month,nv.valuation))
    frh=sorted((amfi or {}).get('history') or [])
    def fr_at(m):   # AMFI data lags a month: carry the latest reading forward up to 2 months
        c=[(mm,v) for mm,v in frh if mm<=m and v is not None]
        if not c: return None
        y,mo=map(int,m.split('-')); y2,mo2=map(int,c[-1][0].split('-'))
        return c[-1][1] if (y*12+mo)-(y2*12+mo2)<=2 else None
    hist_items=[it for it in items if len(it.get('history') or [])>12]
    months=sorted({m for it in hist_items for m,_ in it['history']})
    out=[]
    for m in months:
        sc=[v for it in hist_items for mm,v in it['history'] if mm==m and v is not None]
        breadth=50+50*(sum(v>65 for v in sc)-sum(v<=35 for v in sc))/len(sc) if sc else None
        parts={'Nifty 50 valuation':num(nval.get(m)),'Thematic-fund froth':num(fr_at(m)),'Rich minus cheap readings':None if breadth is None else round(breadth,1)}
        have=[v for v in parts.values() if v is not None]
        if len(have)>=2: out.append({'month':m,'score':round(sum(have)/len(have),1),'parts':parts})
    if not out: return None
    cur=dict(out[-1]); para=[it['name'] for it in items if it['model']!='stocks' and (it.get('parabolic') or {}).get('status') in ('Parabolic','Stretched')]
    cur['stretched']=para
    return {'now':cur,'history':[[x['month'],x['score']] for x in out]}
mood_=mood()

out={'mood':mood_,'proxy_backtest':proxy,'track':track,'backtest':bt,'built_at':datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),'models':meta,'run_prices':run_prices,'prices':prices,'items':items,'assetClasses':ac,'parabolic':parabolic,'amfi':amfi,'watchlist':watchlist,'size_rotation':size_rotation}
os.makedirs(os.path.join(ROOT,'data'),exist_ok=True)
json.dump(out,open(os.path.join(ROOT,'data','signals.json'),'w'),separators=(',',':'),allow_nan=False)
print('signals.json:',len(items),'items;',{k:v['asof'] for k,v in meta.items()})
