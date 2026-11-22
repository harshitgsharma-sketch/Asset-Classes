import pandas as pd, json, math
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
def tier(h,c):
    if h>12: return 'A'
    return 'B' if (c is not None and c>=0.8) else 'C'
# core: gold, nifty
for key,f,nm in [('GOLD','gold-score-log.csv','Gold'),('NIFTY50','nifty-score-log.csv','Nifty 50')]:
    d=pd.read_csv(C+f); r=d.iloc[-1]; h=hist(d)
    add(id=key,name=nm,model='core',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r.filter)},history=h,coverage=num(r.coverage),tier='A',action=None,meta={'Source':r.source},flags='History before Nov-2026 reconstructed (±3 pts)')
# sectors
d=pd.read_csv(C+'nifty-sectors-score-log.csv')
for _,r in d.iterrows():
    add(id='SEC_'+r['index'],name=r['name'],model='sectors',score=num(r.absolute),signal=r.signal,buckets={'Valuation':num(r.valuation),'Sector cycle':num(r.sector_cycle),'Timing':num(r.timing),'Filter':num(r['filter']),'Relative vs Nifty':num(r.relative)},history=[],coverage=num(r.coverage),tier='B' if r.coverage>=0.8 else 'C',action=r.quadrant,meta={'PE':num(r.pe),'Core indicators':r.core_of_17+' (v1)'},flags=r.flags if isinstance(r.flags,str) else '')
# factors
d=pd.read_csv(P+'nifty-factors-score-log.csv')
for _,r in d.iterrows():
    add(id='FAC_'+r['index'],name=r['name'],model='factors',score=num(r.absolute),signal=r.signal,buckets={'Valuation':num(r.valuation),'Factor cycle':num(r.factor_cycle),'Timing':num(r.timing),'Filter':num(r['filter']),'Relative vs Nifty':num(r.relative)},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.quadrant,meta={'PE':num(r.pe),'Indicators':r.indicators},flags=r.flags if isinstance(r.flags,str) else '')
# stocks
d=pd.read_csv(P+'nifty200-stocks-score-log.csv')
for _,r in d.iterrows():
    c=cov(r.coverage)
    add(id='STK_'+r.ticker,name=r['name'],model='stocks',score=num(r.score) if 'NOT RATED' not in r.signal else None,signal=r.signal,buckets={'Valuation':num(r.valuation),'Quality':num(r.quality),'Momentum':num(r.momentum)},history=[],coverage=c,tier=tier(1,c),action=None,meta={'Ticker':r.ticker,'Sector':r.sector,'PE':num(r.pe),'Sector PE':num(r.sector_pe)},sidx=r.sector_index,flags=r.flags if isinstance(r.flags,str) else '')
# global
d=pd.read_csv(C+'global-indices-score-log.csv')
for _,r in d.iterrows():
    nm=r['name'] if r['index']!='NIFTY50' else 'Nifty 50 (global 5-yr lens)'
    add(id='GLB_'+r['index'],name=f"{nm}" ,model='global',score=num(r.five_yr),signal=r.signal,buckets={'Valuation':num(r.valuation),'Macro':num(r.macro),'Currency':num(r.currency),'Timing':num(r.timing),'Filter':num(r['filter'])},history=[],coverage=num(r.coverage),tier=tier(1,num(r.coverage)),action=r.entry_plan,meta={'Economy':r.economy,'Exp. INR return % p.a. (net)':num(r.exp_inr_net),'Range':r.exp_inr_range if isinstance(r.exp_inr_range,str) else None,'Access':r.access},flags=r.flags if isinstance(r.flags,str) else '')
# commodities
d=pd.read_csv(P+'commodities-score-log.csv')
for c,nm in [('SILVER','Silver'),('BRENT','Brent crude'),('COPPER','Copper')]:
    s=d[d.commodity==c]; r=s.iloc[-1]; h=hist(s)
    add(id='CMD_'+c,name=nm,model='commodities',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=h if len(h)>1 else [],coverage=num(r.coverage),tier=tier(len(h),num(r.coverage)),action=None,meta={'Price (USD)':num(r.price_usd),'Indicators live':r.live},flags='Month in progress; history reconstructed' if len(h)>1 else 'Only one month of history')
# btc
d=pd.read_csv(P+'btc-score-log.csv'); r=d.iloc[-1]
add(id='BTC',name='Bitcoin',model='crypto',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Timing':num(r.timing),'Filter':num(r['filter'])},history=hist(d),coverage=num(r.coverage),tier='A',action='Stage entries; cap at 5% of portfolio; 31.2% VDA tax, no loss set-off',meta={'Price (₹ lakh)':num(r.btc_inr_lakh)},flags='History reconstructed; macro filter high (79)')
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
    add(id='RE_'+r.key,name=r['name'],model='reits',score=num(r.oscillator),signal=r.signal,buckets={'Valuation':num(r.valuation),'Filter':num(r['filter']),'Timing':num(r.timing)},history=[],coverage=c,tier=tier(1,c),action=None,meta={'Type':r.family,'Distribution yield %':num(r.dist_yield_pct),'Spread vs G-sec (pp)':num(r.spread_vs_gsec_pp),'Price/NAV':num(r.price_to_nav),'Post-tax yield %':num(r.post_tax_yield_pct)},flags=r.flags if isinstance(r.flags,str) else '')
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
 'stocks':('nifty200-stocks-score-log.csv',35,'monthly Claude run (3rd)'),
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
        parabolic={'built_at':pj['built_at'],'rule':pj['rule'],'summary':pj['summary']}
    except Exception as e:
        print('WARN parabolic.json unreadable:',e)
out={'built_at':datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),'models':meta,'run_prices':run_prices,'prices':prices,'items':items,'assetClasses':ac,'parabolic':parabolic}
os.makedirs(os.path.join(ROOT,'data'),exist_ok=True)
json.dump(out,open(os.path.join(ROOT,'data','signals.json'),'w'),separators=(',',':'),allow_nan=False)
print('signals.json:',len(items),'items;',{k:v['asof'] for k,v in meta.items()})
