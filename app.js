const DATA = window.__DATA__;
/* ---------- FRESHNESS + LIVE PRICES (recomputed on every load) ---------- */
const TODAY=new Date();
const fmtD=s=>new Date(s+'T00:00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
function ageDays(s){return Math.floor((TODAY-new Date(s+'T00:00:00'))/864e5)}
function modelStatus(k){const m=(DATA.models||{})[k];if(!m||!m.asof)return {cls:'due',txt:'unknown',age:null};const a=ageDays(m.asof);return a<=m.cadence_days?{cls:'ok',txt:'Fresh',age:a}:a<=m.cadence_days+10?{cls:'due',txt:'Refresh due',age:a}:{cls:'stale',txt:'Stale',age:a}}
const PRICE_META={gold_usd:['Gold','USD/oz','Gold & Nifty 50'],silver_usd:['Silver','USD/oz','Commodities'],brent_usd:['Brent crude','USD/bbl','Commodities, Nifty 50'],copper_usd_t:['Copper','USD/t','Commodities'],btc_usd:['Bitcoin','USD','Bitcoin'],usdinr:['USD/INR','₹','Gold, global, Bitcoin, asset classes'],nifty:['Nifty 50','index','Nifty 50, sectors, factors']};
const LIVE={};
function latestPrice(k){if(LIVE[k])return LIVE[k];const v=DATA.prices&&DATA.prices.values&&DATA.prices.values[k];return v?{value:v.value,source:v.source,at:v.at}:null}
function healthHTML(){
  const keys=Object.keys(PRICE_META);
  const rows=keys.map(k=>{const run=(DATA.run_prices||{})[k],lp=latestPrice(k);const ch=run&&lp?100*(lp.value/run-1):null;
    return `<tr><td><b>${PRICE_META[k][0]}</b> <span class="tag">${PRICE_META[k][1]}</span></td><td style="text-align:right">${run??'–'}</td><td style="text-align:right">${lp?(+lp.value).toLocaleString('en-IN',{maximumFractionDigits:2}):'–'}</td><td style="text-align:right">${ch==null?'–':`<b>${ch>0?'+':''}${ch.toFixed(1)}%</b>`}</td><td>${ch!=null&&Math.abs(ch)>=5?'<span class="stat due">Big move: scores may be out of date</span>':''}</td><td class="tag">${PRICE_META[k][2]}</td><td class="tag">${lp?esc(lp.source)+(lp.at?' · '+new Date(lp.at).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):''):'not fetched yet'}</td></tr>`}).join('');
  const mrows=MODEL_ORDER.map(k=>{const m=(DATA.models||{})[k]||{},s=modelStatus(k);return `<tr><td><b>${MODELS[k]}</b></td><td style="white-space:nowrap">${m.asof?fmtD(m.asof):'–'}</td><td style="text-align:right;white-space:nowrap">${s.age==null?'–':s.age+(s.age===1?' day':' days')}</td><td><span class="stat ${s.cls}">${s.txt}</span></td><td class="tag">${esc(m.refresh||'')}</td></tr>`}).join('');
  return `<div class="grid g2" style="margin-top:14px">
  <section class="card"><h2>Prices since the last scoring run</h2><p class="hint">Checked every time the page opens. A move of 5% or more means the score was set at a different price; it updates on the next model run.</p>
  <table><thead><tr><th>Asset</th><th style="text-align:right">At scoring</th><th style="text-align:right">Latest</th><th style="text-align:right">Change</th><th></th><th>Feeds</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></section>
  <section class="card"><h2>Data freshness by model</h2><p class="hint">How old each model's inputs are today, against how often they should be refreshed.</p>
  <table><thead><tr><th>Model</th><th>Inputs as of</th><th style="text-align:right">Age</th><th>Status</th><th>Refreshed by</th></tr></thead><tbody>${mrows}</tbody></table></section></div>`;
}
function freshLine(){
  const st=MODEL_ORDER.map(modelStatus),bad=st.filter(s=>s.cls!=='ok').length;
  const built=DATA.built_at?new Date(DATA.built_at).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'–';
  const pf=DATA.prices&&DATA.prices.fetched_at?new Date(DATA.prices.fetched_at).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'not yet';
  const nx=new Date(TODAY.getFullYear(),TODAY.getMonth()+(TODAY.getDate()>3?1:0),3);
  document.getElementById('fresh').innerHTML=`Rebuilt ${built} · prices ${pf} · ${bad?`<span class="stat due">${bad} model${bad>1?'s':''} need refresh</span>`:'<span class="stat ok">all models fresh</span>'} · next model run ${nx.toLocaleDateString('en-IN',{day:'numeric',month:'short'})}`;
}
/* live prices straight from the browser where the source allows it */
async function fetchLive(){
  const ctl=new AbortController();setTimeout(()=>ctl.abort(),6000);const fetch=(u)=>window.fetch(u,{signal:ctl.signal});
  const tasks=[
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd').then(r=>r.json()).then(j=>{LIVE.btc_usd={value:j.bitcoin.usd,source:'CoinGecko, live',at:new Date().toISOString()}}),
    fetch('https://api.frankfurter.app/latest?from=USD&to=INR').then(r=>r.json()).then(j=>{LIVE.usdinr={value:j.rates.INR,source:'ECB reference, live',at:new Date().toISOString()}}),
  ];
  await Promise.allSettled(tasks);
  freshLine();if(CUR.tab==='snapshot'||CUR.tab==='commod'||CUR.tab==='crypto')route()
}
const BANDS=[['Strong buy',0,20,'--b1'],['Buy',20,35,'--b2'],['Accumulate',35,50,'--b3'],['Hold',50,65,'--b4'],['Trim',65,80,'--b5'],['Exit',80,100,'--b6']];
const MODELS={core:'Gold & Nifty 50',sectors:'Nifty sectors & size',factors:'Nifty factors',stocks:'Stocks',global:'Global markets',commodities:'Commodities',crypto:'Bitcoin',bonds:'Bonds & deposits',carry:'Arbitrage & covered call',reits:'REITs & InvITs',property:'Housing by city'};
const MODEL_ORDER=['core','sectors','factors','stocks','global','commodities','crypto','bonds','carry','reits','property'];
const TIERS={A:'High: multi-year history (reconstructed), full scoring',B:'Medium: one month, most inputs live',C:'Low: one month, partial or estimated inputs'};
const TIERNAME={A:'High',B:'Medium',C:'Low'};
const bandOf=s=>s==null?null:BANDS.find(b=>s<=b[2])||BANDS[5];
const bcol=s=>{const b=bandOf(s);return b?`var(${b[3]})`:'var(--line-2)'};
/* Stock universe on the board: the Nifty 50 plus the watchlist. The pipeline still scores the
   whole Nifty 500; set STOCK_UNIVERSE to 'nifty500' to show those stocks again. */
const STOCK_UNIVERSE='nifty50';
const FULL_ITEMS=DATA.items.filter(i=>i.score!=null&&!(STOCK_UNIVERSE==='nifty50'&&i.model==='stocks'&&i.meta&&i.meta.Universe==='Nifty 500'&&!i.watch));
/* Nifty 500 stocks outside the Nifty 50 are on the map, list, search and sector chart, but kept out of the headline counts and signal lanes so 450 stocks do not swamp the other models. */
FULL_ITEMS.forEach(i=>{i.wide=i.model==='stocks'&&(i.meta||{}).Universe!=='Nifty 50'});
/* Blue bands only by default: Hold, Trim and Exit readings (score 50 and up) are hidden across the
   whole board until the header switch turns them on. The choice is kept in this browser. */
const INVEST_MAX=50;   // top of Accumulate: below this a reading sits in a blue band
let SHOW_ALL=false;try{SHOW_ALL=localStorage.getItem('eeb-show-all')==='1'}catch(e){}
const inBlue=s=>SHOW_ALL||(s!=null&&s<INVEST_MAX);
const VBANDS=()=>BANDS.filter(b=>SHOW_ALL||b[1]<INVEST_MAX);   // always a prefix of BANDS, so indexes match
const GTOP=()=>SHOW_ALL?100:INVEST_MAX;                          // right-hand end of gauges
const HIDDEN_NOTE='Hold, Trim and Exit readings are hidden. Use <b>Show Hold, Trim &amp; Exit</b> at the top to see them.';
let ALL_ITEMS=FULL_ITEMS.filter(i=>inBlue(i.score));
let items=ALL_ITEMS;   // narrowed to the open tab's scope by the router
const byId=Object.fromEntries(DATA.items.map(i=>[i.id,i]));
const pct=x=>Math.round(x*100)+'%';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const notInvestable=i=>/Not investable/i.test(i.action||'');
const investable=i=>i.score!=null&&inBlue(i.score)&&!notInvestable(i);
/* ---------- SIGNAL MEASURES ---------- */
const CW={A:1,B:.8,C:.55};
const LANES={buy:['Buy now','Cheap, timing and macro not against it'],stage:['Buy in stages','Cheap, but timing or macro argues against a lump sum'],near:['On the cusp','Within 3 points of the Buy (35) or Trim (65) line'],rally:['Trim into rallies','Rich, timing not yet against it'],trimnow:['Trim now','Rich, and timing has turned']};
items.forEach(i=>{
  const s=i.score,bk=Object.entries(i.buckets||{}).filter(([k,v])=>v!=null&&!/Relative/.test(k));
  i.T=i.buckets?.Timing??i.buckets?.Momentum??null; i.V=i.buckets?.Valuation??null; i.F=i.buckets?.Filter??null;
  i.ext=Math.min(1,Math.abs(s-50)/40);
  i.agreeN=bk.filter(([k,v])=>s<50?v<50:v>50).length; i.bkN=bk.length;
  i.agree=bk.length?i.agreeN/bk.length:.5;
  i.conv=Math.round(100*i.ext*(.4+.6*i.agree)*CW[i.tier]);
  i.side=s<=50?'buy':'sell';
  if(i.history&&i.history.length>3){const h=i.history;i.d1=+(s-h[h.length-2][1]).toFixed(1);i.d3=+(s-h[h.length-4][1]).toFixed(1)}
  const a=i.action||'';
  if(s<=35)i.lane=/Park new money|Buy floating/.test(a)?'buy':(/tranche|thirds|stage|Stage/.test(a)||(i.T!=null&&i.T>55)||(i.F!=null&&i.F>65))?'stage':'buy';
  else if(s>65)i.lane=/Trim now/.test(a)?'trimnow':/rallies/.test(a)?'rally':(i.T==null||i.T>=55)?'trimnow':'rally';
  else if(s<=38||s>62)i.lane='near';
  if(notInvestable(i))i.lane=null;
});
const convWord=c=>c>=55?'Strong':c>=35?'Moderate':'Weak';
function renderChrome(){
  document.getElementById('nsig').textContent=SHOW_ALL?`${FULL_ITEMS.length} readings from 11 models`:`${ALL_ITEMS.length} of ${FULL_ITEMS.length} readings shown (blue bands) from 11 models`;
  const sc=document.getElementById('scale');sc.style.gridTemplateColumns=`repeat(${VBANDS().length},auto)`;
  sc.innerHTML=VBANDS().map(b=>`<div title="${b[0]}: ${b[1]===0?'1–20':b[2]===100?'81–100':(b[1]+1)+'–'+b[2]}"><span style="background:var(${b[3]})"></span><b class="lbl">${b[0]}</b><em class="rng">${b[1]===0?'1–20':b[2]===100?'81–100':(b[1]+1)+'–'+b[2]}</em></div>`).join('');
  let t=document.getElementById('showall');
  if(!t){t=document.createElement('button');t.id='showall';t.className='btn';sc.insertAdjacentElement('afterend',t);
    t.onclick=()=>{SHOW_ALL=!SHOW_ALL;try{localStorage.setItem('eeb-show-all',SHOW_ALL?'1':'0')}catch(e){}
      ALL_ITEMS=FULL_ITEMS.filter(i=>inBlue(i.score));renderChrome();route()}}
  t.textContent=SHOW_ALL?'Hide Hold, Trim & Exit':'Show Hold, Trim & Exit';t.setAttribute('aria-pressed',String(SHOW_ALL));t.classList.toggle('on',SHOW_ALL);
}
renderChrome();

/* tooltip */
const tt=document.getElementById('tt');
function showTT(e,html){tt.innerHTML=html;tt.style.display='block';const x=Math.min(e.clientX+14,innerWidth-300),y=Math.min(e.clientY+14,innerHeight-tt.offsetHeight-10);tt.style.left=x+'px';tt.style.top=y+'px'}
function hideTT(){tt.style.display='none'}
function chip(s){const b=bandOf(s);return `<span class="chip"><span class="sw" style="background:var(${b[3]})"></span>${b[0]}</span>`}
function tierTag(t){const n={A:3,B:2,C:1}[t];return `<span class="conf" title="Confidence ${TIERS[t]}" aria-label="Confidence ${TIERNAME[t]}">${[0,1,2].map(k=>`<i class="${k<n?'':'o'}"></i>`).join('')}</span>`}

function bindRows(root){root.querySelectorAll('[data-id]').forEach(el=>{el.onclick=()=>openDrawer(el.dataset.id);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openDrawer(el.dataset.id)}}})}

/* holdings: one viewer's convenience, kept in this browser only */
let HELD=new Set();try{HELD=new Set(JSON.parse(localStorage.getItem('eeb-held')||'[]'))}catch(e){}
function saveHeld(){try{localStorage.setItem('eeb-held',JSON.stringify([...HELD]))}catch(e){}}
function toggleHeld(id){HELD.has(id)?HELD.delete(id):HELD.add(id);saveHeld();openDrawer(id);route(true)}


/* sparkline */
function spark(h,w,ht){
  if(!h||h.length<2)return '';
  const xs=k=>k*(w-4)/(h.length-1)+2, ys=v=>ht-2-(v/100)*(ht-4);
  const d=h.map((p,k)=>(k?'L':'M')+xs(k).toFixed(1)+','+ys(p[1]).toFixed(1)).join('');
  const last=h[h.length-1][1];
  return `<svg width="${w}" height="${ht}" viewBox="0 0 ${w} ${ht}" style="max-width:100%;height:auto" aria-hidden="true"><rect x="0" y="${ys(35)}" width="${w}" height="${ys(0)-ys(35)}" fill="var(--b3)" opacity=".35"/><rect x="0" y="${ys(100)}" width="${w}" height="${ys(65)-ys(100)}" fill="var(--b5)" opacity=".3"/><path d="${d}" fill="none" stroke="var(--ink)" stroke-width="1.5"/><circle cx="${xs(h.length-1)}" cy="${ys(last)}" r="3" fill="${bcol(last)}" stroke="var(--ink)" stroke-width="1"/></svg>`;
}

function bindDots(el){el.querySelectorAll('.dot').forEach(g=>{const i=byId[g.dataset.id];
  const tip=`<b>${esc(i.name)}</b><br>Score ${i.score} · ${bandOf(i.score)[0]}<br>Valuation ${i.V??'–'} · Timing ${i.T??'–'}${i.F!=null?' · Macro '+i.F:''}<br>Signal strength ${i.conv} (${convWord(i.conv)}) · confidence ${TIERNAME[i.tier]}`;
  g.onmousemove=e=>showTT(e,tip);g.onmouseleave=hideTT;g.onclick=()=>{hideTT();openDrawer(i.id)};
  g.onfocus=()=>{const r=g.getBoundingClientRect();showTT({clientX:r.right,clientY:r.top},tip)};g.onblur=hideTT;
  g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hideTT();openDrawer(i.id)}}})}
function drawSX(){
  const el=document.getElementById('sxsvg');if(!el)return;
  const stocks=items.filter(i=>i.model==='stocks'&&i.sidx&&byId['SEC_'+i.sidx]&&inBlue(byId['SEC_'+i.sidx].score));
  const rows=[...new Set(stocks.map(i=>i.sidx))].filter(k=>stocks.filter(i=>i.sidx===k).length>=2).map(k=>{const st=stocks.filter(i=>i.sidx===k).sort((a,b)=>a.score-b.score);const med=st.length%2?st[(st.length-1)/2].score:(st[st.length/2-1].score+st[st.length/2].score)/2;return {sec:byId['SEC_'+k],st,med:+med.toFixed(1)}}).sort((a,b)=>Math.abs(b.sec.score-b.med)-Math.abs(a.sec.score-a.med));
  const W=el.clientWidth,L=190,R=150,rh=34,T=22;const x=v=>L+(v-1)/99*(W-L-R);
  let s=`<svg width="${W}" height="${T+rows.length*rh+20}" role="group" aria-label="Sector scores against their stocks">`;
  VBANDS().forEach((b,k)=>s+=`<rect x="${x(Math.max(1,b[1]))}" y="${T-4}" width="${x(b[2])-x(Math.max(1,b[1]))}" height="${rows.length*rh}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/><text x="${(x(Math.max(1,b[1]))+x(b[2]))/2}" y="12" text-anchor="middle">${b[0]}</text>`);
  s+=`<text x="${W-R+12}" y="12">Gap · spread</text>`;
  rows.forEach((r,k)=>{const cy=T+k*rh+rh/2-4,gap=r.med-r.sec.score,spread=(r.st[r.st.length-1].score-r.st[0].score).toFixed(0);
    s+=`<line x1="0" x2="${W}" y1="${cy+rh/2}" y2="${cy+rh/2}" stroke="var(--line)"/><text x="0" y="${cy+4}" style="fill:var(--ink);font-size:12px">${esc(r.sec.name)} <tspan style="fill:var(--ink-3)">(${r.st.length})</tspan></text>`;
    s+=`<line x1="${x(r.st[0].score)}" x2="${x(r.st[r.st.length-1].score)}" y1="${cy}" y2="${cy}" stroke="var(--ink-3)" stroke-width="1"/>`;
    r.st.forEach(i=>s+=`<g class="dot" data-id="${i.id}" tabindex="0" role="button" aria-label="${esc(i.name)} ${i.score}"><circle cx="${x(i.score)}" cy="${cy}" r="9" fill="transparent"/><circle cx="${x(i.score)}" cy="${cy}" r="4" fill="${bcol(i.score)}" stroke="var(--surface)" stroke-width="1"/></g>`);
    s+=`<path d="M${x(r.med)},${cy-6} l6,6 l-6,6 l-6,-6 z" fill="var(--surface)" stroke="var(--ink)" stroke-width="1.5"/>`;
    s+=`<g class="dot" data-id="${r.sec.id}" tabindex="0" role="button" aria-label="${esc(r.sec.name)} index ${r.sec.score}"><circle cx="${x(r.sec.score)}" cy="${cy}" r="10" fill="transparent"/><circle cx="${x(r.sec.score)}" cy="${cy}" r="7" fill="${bcol(r.sec.score)}" stroke="var(--ink)" stroke-width="1.6"/></g>`;
    s+=`<text x="${W-R+12}" y="${cy+4}" style="fill:var(--ink)">${gap>0?'+':''}${gap.toFixed(1)} · ${spread} pts ${Math.abs(gap)>=10?'⚑':''}</text>`});
  s+='</svg>';el.innerHTML=s;bindDots(el);
}



/* ---------- TRENDS ---------- */
const SERIES_ALL=[['GOLD','--s1'],['NIFTY50','--s2'],['CMD_SILVER','--s3'],['CMD_BRENT','--s4'],['BTC','--s5']];
let SERIES=SERIES_ALL;
let trendState={on:{GOLD:1,NIFTY50:1,CMD_SILVER:1,CMD_BRENT:0,BTC:0},range:36};
function viewTrends(){
  SERIES=SERIES_ALL.filter(([id])=>items.includes(byId[id]));
  if(!SERIES.length)return `<div class="card"><div class="empty">Nothing in this tab has monthly history yet. History builds after each monthly run.</div></div>`;
  if(SERIES.length<SERIES_ALL.length&&!SERIES.some(([id])=>trendState.on[id]))SERIES.forEach(([id])=>trendState.on[id]=1);
  return `<div class="card" style="margin-bottom:14px"><h2>Oscillator history with entry/exit zones</h2>
  <p class="hint">Only gold, the Nifty 50, silver, Brent and Bitcoin have monthly history, and everything before Nov-2026 is reconstructed (about ±3 points), not live. Toggle series; hover for values.</p>
  <div class="filters"><span id="stog">${SERIES.map(([id,c])=>`<span class="toggle ${trendState.on[id]?'':'off'}" data-id="${id}" style="margin-right:6px"><span class="sw" style="background:var(${c})"></span>${esc(byId[id].name)}</span>`).join('')}</span>
  <span class="seg" id="rseg"><button data-v="12">1 yr</button><button data-v="36">3 yr</button><button data-v="61">5 yr</button></span></div>
  <div id="tsvg"></div></div>`;
}
function drawTrends(){
  const el=document.getElementById('tsvg');if(!el)return;
  const W=el.clientWidth,H=300,L=34,R=90,T=10,B=26;
  const months=byId.GOLD.history.map(h=>h[0]).slice(-trendState.range);
  const x=k=>L+k*(W-L-R)/(months.length-1),y=v=>T+(100-v)/100*(H-T-B);
  let s=`<svg width="${W}" height="${H}" role="img" aria-label="Oscillator history">`;
  VBANDS().forEach((b,k)=>s+=`<rect x="${L}" y="${y(b[2])}" width="${W-L-R}" height="${y(b[1])-y(b[2])}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/>`);
  [20,35,50,65,80].forEach(v=>s+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line-2)"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${v}</text>`);
  months.forEach((m,k)=>{if(m.endsWith('-01')||k===months.length-1)s+=`<text x="${x(k)}" y="${H-8}" text-anchor="middle">${k===months.length-1?'Nov-26':m.slice(0,4)}</text>`});
  const nk=months.indexOf('2026-11');if(nk>0)s+=`<line x1="${x(nk-1)}" x2="${x(nk-1)}" y1="${T}" y2="${H-B}" stroke="var(--ink-3)" stroke-dasharray="3 3"/><text x="${x(nk-1)-4}" y="${T+10}" text-anchor="end">reconstructed ← | → live</text>`;
  const labels=[];
  SERIES.forEach(([id,c])=>{if(!trendState.on[id])return;const map=Object.fromEntries(byId[id].history);
    let d='',started=false;months.forEach((m,k)=>{const v=map[m];if(v==null){started=false;return}d+=(started?'L':'M')+x(k).toFixed(1)+','+y(v).toFixed(1);started=true});
    s+=`<path d="${d}" fill="none" stroke="var(${c})" stroke-width="2"/>`;const lv=map['2026-11'];
    s+=`<circle cx="${x(months.length-1)}" cy="${y(lv)}" r="4" fill="var(${c})" stroke="var(--surface)" stroke-width="2"/>`;labels.push([y(lv),`${byId[id].name} ${lv}`])});
  labels.sort((a,b)=>a[0]-b[0]);for(let k=1;k<labels.length;k++)if(labels[k][0]-labels[k-1][0]<13)labels[k][0]=labels[k-1][0]+13;
  labels.forEach(l=>s+=`<text x="${W-R+8}" y="${l[0]+4}" style="fill:var(--ink)">${esc(l[1])}</text>`);
  s+=`<line id="xh" x1="0" x2="0" y1="${T}" y2="${H-B}" stroke="var(--ink-2)" style="display:none"/><rect id="ov" x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="transparent"/></svg>`;
  el.innerHTML=s;
  const ov=el.querySelector('#ov'),xh=el.querySelector('#xh');
  ov.onmousemove=e=>{const r=ov.getBoundingClientRect();const k=Math.round((e.clientX-r.left)/(r.width)*(months.length-1));const m=months[Math.max(0,Math.min(months.length-1,k))];xh.setAttribute('x1',x(months.indexOf(m)));xh.setAttribute('x2',x(months.indexOf(m)));xh.style.display='';
    showTT(e,`<b>${m}</b>`+SERIES.filter(([id])=>trendState.on[id]).map(([id])=>{const v=Object.fromEntries(byId[id].history)[m];return `<br>${esc(byId[id].name)}: ${v??'n/a'}${v!=null?' · '+bandOf(v)[0]:''}`}).join(''))};
  ov.onmouseleave=()=>{xh.style.display='none';hideTT()};
}
function bindTrends(){
  document.querySelectorAll('#stog .toggle').forEach(t=>t.onclick=()=>{trendState.on[t.dataset.id]^=1;t.classList.toggle('off');drawTrends()});
  document.querySelectorAll('#rseg button').forEach(b=>{b.classList.toggle('on',+b.dataset.v===trendState.range);b.onclick=()=>{trendState.range=+b.dataset.v;bindTrends()}});
  drawTrends();
}


/* ---------- NOTES ---------- */
function viewNotes(){
  const thin=[['Gold, Nifty 50','61 months (pre-Nov reconstructed)','72–88%','No'],['Silver, Brent','61 / 49 months (reconstructed)','57–72%','No'],['Bitcoin','61 months (reconstructed)','64%','No'],['Copper','1 month','–','No'],['Nifty sectors (20)','1 month','7 of 17 core indicators','No'],['Factors (10)','1 month','12/12; PE percentile estimated','No'],['Nifty 500 stocks','1 month','9/10 per stock; Nifty 50 from screener.in, the rest from Yahoo Finance (3-yr EPS window); own-median PE not sourced','No'],['Global markets (24)','1 month','27–85%; 13 markets rest on one valuation input','No'],['Bonds (7) and carry (2)','1 month','Full; carry vol estimated','No'],['REITs & InvITs (12)','1 month','3–7 of 7; SM-REITs have no live price','No'],['Housing by city (9)','1 snapshot','Valuation only, quarterly data','No'],['Asset classes (15)','1 month','Valuation only, judgment anchors','No']];
  return `<div class="card prose">
  <h2 style="margin-top:0">The concept in one line</h2>
  <p>One page that answers, every month: <strong>what should I add to, what should I trim, what changed, and how much should I trust it?</strong> Everything sits on the same 1–100 scale, so a bond, a REIT, a sector and Bitcoin can be compared on one axis.</p>
  <h2>Information hierarchy</h2>
  <ol><li><strong>This month</strong> (the landing view): count of readings by band, band changes since last month, an "add" list and a "trim if you hold it" list, and where models disagree. This is the 2-minute read after each monthly refresh.</li>
  <li><strong>Opportunity map</strong>: every instrument as a dot on the 1–100 scale, one row per model. The pattern you look for is clusters at the edges.</li>
  <li><strong>Asset classes</strong>: the top-down allocation view. Valuation-only rank against each dedicated model's full oscillator, so you see when timing disagrees with value.</li>
  <li><strong>Drill-down</strong> (side panel from anywhere): score, band, the model's own action, bucket bars (valuation / timing / filter and model-specific ones), history, key facts, caveats and a confidence tier.</li>
  <li><strong>Trends</strong> and <strong>Alerts</strong>: history with shaded zones, a band timeline, and rules that fire on band changes, crossings, drift, staging and disagreement.</li></ol>
  <h2>How signals are measured</h2>
  <ul><li><strong>Signal strength (0–100)</strong> = distance from neutral (|score − 50| ÷ 40, capped at 1) × driver agreement (0.4 + 0.6 × share of buckets on the same side of 50) × confidence (High 1, Medium 0.8, Low 0.55). It answers "how loud and how trustworthy is this call", separately from the score itself.</li>
  <li><strong>Action lane</strong>: score ≤35 is "Buy now" unless the model says to stage, timing is above 55 or the macro filter is above 65 ("Buy in stages"). Score >65 is "Trim now" or "Trim into rallies" by the model's own wording, else by timing ≥55. Scores within 3 points of 35 or 65 are "On the cusp".</li>
  <li><strong>Drivers strip</strong>: one square per bucket, coloured by band, so you can see at a glance whether valuation, timing and macro agree.</li>
  <li><strong>Momentum</strong>: 1- and 3-month change, only for the five models with history.</li>
  <li>These weights are a starting proposal, not calibrated; they need a back-test before you lean on them.</li></ul>
  <h2>Design choices</h2>
  <ul><li><strong>One colour scale, everywhere.</strong> Blue = cheap, grey = hold, red = rich. Colour is always paired with the band name or number, never colour alone.</li>
  <li><strong>Confidence is visible, not footnoted.</strong> High (multi-year history), Medium (one month, most inputs live), Low (thin or estimated inputs), shown as three dots beside every reading. Hollow dots on the map are Low. Today ${Math.round(100*items.filter(i=>i.tier!=='A').length/items.length)}% of readings are one month old.</li>
  <li><strong>Action text comes from the models</strong> ("Enter in 3 tranches over ~6 m", "Park new money here"), not from the dashboard. The dashboard ranks and routes; the models decide.</li>
  <li><strong>Built for a ≤5-year INR holder</strong>: global scores are already INR-adjusted, carry and REIT yields are shown post-tax, and Bitcoin carries its 5% cap and VDA tax note.</li></ul>
  <h2>What it needs to become real</h2>
  <ul><li><strong>Your holdings</strong> (even a simple CSV of asset and weight). That turns "consider trimming" into "you hold Pharma at 8%, it's in Trim", and enables position-size and cap alerts. This is the single biggest upgrade.</li>
  <li><strong>A combined readings file</strong> written by the monthly refresh on the 3rd, so the board reads one file instead of eleven logs.</li>
  <li><strong>History accrues on its own</strong>: by Feb-2027 every model has three months, enough for drift alerts; by late 2027 a year, enough to trust band changes.</li></ul>
  <h2>Where the data is thin today</h2>
  <table><tr><th>Model</th><th>History</th><th>Coverage</th><th>Back-tested</th></tr>${thin.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</table>
  <p style="margin-top:10px">Mid-range scores (36–65) are close to neutral in every model; the readings are most useful at the extremes. Not investment advice: anchors are judgment-based.</p></div>`;
}

/* ---------- KNOWLEDGE ---------- */
let KNOW=null,MARKED=null;
function loadMarked(){if(MARKED)return MARKED;MARKED=new Promise((ok,no)=>{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js';s.onload=()=>ok(window.marked);s.onerror=()=>{MARKED=null;no(new Error('could not load the Markdown renderer'))};document.head.appendChild(s)});return MARKED}
function viewKnowledge(){return `<div class="know"><div class="card klist" id="klist"><h2>Notes</h2><p class="hint">Loading…</p></div><div class="card prose kbody" id="kbody"><p class="hint">Loading…</p></div></div>`}
async function drawKnowledge(){
  const list=document.getElementById('klist'),body=document.getElementById('kbody');
  const slug=decodeURIComponent((location.hash.split('/')[1])||'');
  try{
    if(!KNOW){const r=await fetch('knowledge/index.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('index '+r.status);KNOW=((await r.json()).notes||[]).sort((a,b)=>(!!b.pinned-!!a.pinned)||(b.added||'').localeCompare(a.added||''))}
    const cur=KNOW.find(n=>n.slug===slug)||KNOW[0];
    list.innerHTML=`<h2>Notes</h2><p class="hint">${KNOW.length} note${KNOW.length===1?'':'s'} · backlog first, then newest</p>${KNOW.map(n=>`<a class="kitem${cur&&n.slug===cur.slug?' on':''}" href="#knowledge/${encodeURIComponent(n.slug)}"${cur&&n.slug===cur.slug?' aria-current="page"':''}><span class="kt">${esc(n.title)}</span><span class="km">${esc(n.source||'')} · ${esc(n.added||'')}</span></a>`).join('')}`;
    if(!cur){body.innerHTML='<p class="hint">No notes yet. Add one to the knowledge/ folder.</p>';return}
    const [md,mk]=await Promise.all([fetch('knowledge/'+cur.file+'?t='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('note '+r.status);return r.text()}),loadMarked()]);
    body.innerHTML=mk.parse(md);
    body.querySelectorAll('a[href]').forEach(a=>{const h=a.getAttribute('href');const m=h.match(/^(?:\.\/)?([\w.-]+)\.md(#.*)?$/);
      if(m){const n=KNOW.find(k=>k.file===m[1]+'.md');a.href=n?'#knowledge/'+encodeURIComponent(n.slug):'https://github.com/harshitgsharma-sketch/Asset-Classes/blob/main/knowledge/'+m[1]+'.md'+(m[2]||'');if(!n){a.target='_blank';a.rel='noopener'}}
      else if(/^(?:\.\.\/)?models\//.test(h)){a.href='https://github.com/harshitgsharma-sketch/Asset-Classes/blob/main/'+h.replace(/^\.\.\//,'');a.target='_blank';a.rel='noopener'}
      else if(/^https?:/.test(h)){a.target='_blank';a.rel='noopener'}});
    window.scrollTo(0,0);
  }catch(e){body.innerHTML=`<p class="hint">Could not load the knowledge notes (${esc(e.message)}). If you opened the file directly, serve the folder instead.</p>`}
}

/* ---------- DRAWER ---------- */
const dr=document.getElementById('drawer');
let lastFocus=null;
function nextBand(s){const b=bandOf(s),k=BANDS.indexOf(b);const dn=k>0?`${(s-b[1]).toFixed(1)} pts above ${BANDS[k-1][0]}`:'';const up=k<5?`${(b[2]-s+0.1).toFixed(1)} pts below ${BANDS[k+1][0]}`:'';return [dn,up].filter(Boolean).join(' · ')}
let drTab='sum';
const DTABS=[['sum','Summary'],['drv','Drivers'],['px','Price'],['fct','Facts']];
function dsec(title,body,extra){return body?`<section class="dsec${extra?' '+extra:''}">${title?`<h4>${title}</h4>`:''}${body}</section>`:''}
function openDrawer(id){
  const i=byId[id];if(!i)return;
  if(!dr.classList.contains('open'))lastFocus=document.activeElement;
  const W=360,x=v=>4+(v-1)/99*(W-8);
  const gauge=`<svg width="${W}" height="30" viewBox="0 0 ${W} 30" style="max-width:100%;height:auto">${BANDS.map(b=>`<rect x="${x(Math.max(1,b[1]))}" y="8" width="${x(b[2])-x(Math.max(1,b[1]))-2}" height="10" rx="2" fill="var(${b[3]})"/>`).join('')}${i.score!=null?`<path d="M${x(i.score)-6},2 L${x(i.score)+6},2 L${x(i.score)},10 Z" fill="var(--ink)"/>`:''}<text x="4" y="29">1 cheap</text><text x="${W-4}" y="29" text-anchor="end">100 rich</text></svg>`;
  const bk=Object.entries(i.buckets||{}).filter(([k,v])=>v!=null);
  const filt=bk.find(b=>b[0]==='Filter');
  const bars=bk.length?`<svg width="${W}" height="${bk.length*28}" style="max-width:100%">${bk.map(([k,v],r)=>`<text x="0" y="${r*28+16}" style="fill:var(--ink)">${k==='Filter'?'Macro filter':k}</text><rect x="130" y="${r*28+6}" width="${W-172}" height="12" rx="3" fill="var(--surface-2)"/><rect x="130" y="${r*28+6}" width="${(W-172)*v/100}" height="12" rx="3" fill="${bcol(v)}"/><text x="${W}" y="${r*28+16}" text-anchor="end" style="fill:var(--ink);font-weight:600">${v}</text>`).join('')}</svg><div class="tag dnote">Each bucket is on 1–100: low supports buying, high argues against it.${filt&&filt[1]>65?' <b>Macro filter is high:</b> stage entries rather than a lump sum.':''}</div>`:'';
  const meta=Object.entries(i.meta||{}).filter(([k,v])=>v!=null&&v!=='');
  const P=i.parabolic,PE=P&&P.last_episode,DD=i.drawdown,A=DATA.amfi;
  const ddWord=d=>d.now>-0.05?'near its high':d.share_of_days_deeper<=0.1?'one of its deepest falls of the decade':d.share_of_days_deeper<=0.3?'deeper than usual':'within its normal range';
  const kv=rows=>`<div class="kv">${rows.filter(Boolean).map(([a,b])=>`<div>${a}</div><div>${b}</div>`).join('')}</div>`;
  const stat=(l,v,s)=>`<div class="mstat"><span>${l}</span><b>${v}</b>${s?`<em>${s}</em>`:''}</div>`;
  // ---- Summary
  const sum=[
    i.action?dsec('',`<div class="dact"><span>Model's action</span>${esc(i.action)}</div>`,'plain'):'',
    i.score!=null?dsec('Signal',`<div class="dsig"><b>${i.conv}</b><span class="cbar" style="width:140px;height:8px"><i style="width:${i.conv}%;background:${i.side==='buy'?'var(--b2)':'var(--b6)'}"></i></span><span>${convWord(i.conv)} ${i.side} signal</span></div>
      <div class="mstats">${stat('Drivers agreeing',i.bkN?`${i.agreeN} of ${i.bkN}`:'—',i.bkN?'point the same way':'single score')}${stat('Momentum',i.d1!=null?`${i.d1>0?'+':''}${i.d1} / ${i.d3>0?'+':''}${i.d3}`:'—',i.d1!=null?'1 month / 3 months':'one month of history')}${stat('From high',DD?(DD.now>-0.0005?'At high':pct(DD.now)):'—',DD?(DD.now<=-0.0005?ddWord(DD):'10-year window'):'no price history')}${stat('Confidence',TIERNAME[i.tier],`weight ×${CW[i.tier]}`)}</div>`):'',
    i.flags?dsec('Model notes',`<div class="tag" style="white-space:normal">${esc(i.flags)}</div>`,'warnbox'):''
  ].join('');
  // ---- Drivers
  const drv=[
    dsec('What drives the score',bars||'<div class="tag">Single score, no buckets.</div>'),
    i.score!=null?dsec('Signal detail',kv([['Distance from neutral',`${Math.abs(i.score-50).toFixed(1)} pts (${Math.round(i.ext*100)}% of full scale)`],['Drivers agreeing',i.bkN?`${i.agreeN} of ${i.bkN} point the same way`:'Single score'],['Confidence weight',`${TIERNAME[i.tier]} (×${CW[i.tier]})`],i.lane?['Action lane',`<b>${LANES[i.lane][0]}</b>`]:null])):'',
    A&&A.froth!=null&&A.applies_to.includes(i.id)?dsec('Thematic-fund froth (S4)',kv([['Reading',`<b>${A.froth}</b> / 100 · ${A.froth>=80?'High':A.froth>=50?'Moderate':'Low'} (peak ${A.peak[1]} in ${A.peak[0]})`],['Sector/thematic inflow',`₹${Math.round(A.them_net_cr).toLocaleString('en-IN')} cr in ${A.month}${A.share_3m!=null?'; '+pct(A.share_3m)+' of equity inflows (3 m)':''}`],['New schemes, 6 m',A.new_schemes_6m]])+`<div class="tag dnote">AMFI data since 2019; part of the Sector cycle bucket. <a href="#knowledge/sector-froth-signals">Why</a></div>`):''
  ].join('');
  // ---- Price
  const px=[
    dsec('Score, last 24 months',i.history&&i.history.length>1?`${spark(i.history.slice(-24),W,90)}<div class="tag dnote">Shaded: Buy zone (≤35) and Trim zone (>65). Before Nov 2026 reconstructed.</div>`:'<div class="tag">One month so far; the trend starts after the next monthly run.</div>'),
    DD?dsec('Distance from high',kv([['Now vs 10-yr high',`<b>${DD.now>-0.0005?'At high':pct(DD.now)}</b>${DD.now<=-0.0005?` · ${DD.years_below_high<0.1?'set recently':DD.years_below_high.toFixed(1)+' yrs since the high'} (${DD.high_date})`:''}`],['How unusual',DD.now<=-0.0005?(DD.share_of_days_deeper<0.005?`<b>Deepest point since ${DD.window_from.slice(0,4)}</b>`:`${pct(DD.share_of_days_deeper)} of days since ${DD.window_from.slice(0,4)} were deeper: ${ddWord(DD)}`):'—'],['Worst fall',`${pct(DD.worst)} (${DD.worst_date})`],['Longest below a high',`${DD.longest_below_high_years.toFixed(1)} yrs`]])+`<div class="tag dnote">Daily closes since ${DD.window_from.slice(0,4)}, ${DD.asof}${DD.stale?' (latest fetch failed)':''}. Context only.</div>`):'',
    P?dsec('Parabolic check',kv([['Above 150-day EMA',`<b>${P.gap>0?'+':''}${pct(P.gap)}</b> · ${P.status==='Normal'?'Normal (flags at +70%)':`<span class="pill">${P.status}</span>`}`],['Highest in the last year',`${P.max_gap_1y>0?'+':''}${pct(P.max_gap_1y)}`],['Past episodes above +70%',P.episodes?`${P.episodes} since ${P.from.slice(0,4)}; last ${PE.start} (peak +${pct(PE.peak_gap)})${PE.ret_after['6m']!=null?`, then ${PE.ret_after['6m']>0?'+':''}${pct(PE.ret_after['6m'])} over 6 m`:''}`:`None since ${P.from.slice(0,4)}`]])+`<div class="tag dnote">Daily, ${P.asof}. Flag only: it does not change the score.</div>`):'',
    (typeof priceLine==='function'&&priceLine(i))?dsec('Live price',priceLine(i)):''
  ].join('');
  // ---- Facts
  const fct=[
    meta.length?dsec('Key facts',kv(meta.map(([k,v])=>[esc(k),esc(v)]))):'',
    dsec('Confidence',kv([['Level',`${tierTag(i.tier)} ${TIERS[i.tier]}`],i.coverage!=null?['Indicator coverage',`${Math.round(i.coverage*100)}%`]:null,['Back-tested','No']]))
  ].join('');
  const panes={sum,drv,px,fct};
  if(!panes[drTab])drTab='sum';
  dr.innerHTML=`<div class="dhead"><button class="x" onclick="closeDrawer()" aria-label="Close">✕</button>
    <div class="tag">${esc(MODELS[i.model])}</div>
    <h2 id="drh">${esc(i.name)}</h2>
    <div class="dscore"><div class="big">${i.score??'–'}</div><div>${i.score!=null?chip(i.score):''}<div class="tag">Model signal: ${esc(i.signal)}</div>${i.score!=null?`<div class="tag">${nextBand(i.score)}</div>`:''}</div>
      <button class="btn dhold ${HELD.has(i.id)?'on':''}" aria-pressed="${HELD.has(i.id)}" onclick="toggleHeld('${i.id}')">${HELD.has(i.id)?'✓ You hold this':'I hold this'}</button></div>
    ${gauge}
    <div class="dtabs" role="tablist" aria-label="Details">${DTABS.map(([k,l])=>`<button role="tab" data-t="${k}" aria-selected="${k===drTab}" class="${k===drTab?'on':''}">${l}</button>`).join('')}</div></div>
  <div class="dbody">${DTABS.map(([k])=>`<div class="dpane" data-t="${k}" role="tabpanel" ${k===drTab?'':'hidden'}>${panes[k]||'<div class="tag">Nothing more for this reading.</div>'}</div>`).join('')}</div>`;
  dr.querySelectorAll('.dtabs button').forEach(b=>b.onclick=()=>{drTab=b.dataset.t;dr.querySelectorAll('.dtabs button').forEach(x=>{const on=x===b;x.classList.toggle('on',on);x.setAttribute('aria-selected',on)});dr.querySelectorAll('.dpane').forEach(p=>p.hidden=p.dataset.t!==drTab);dr.scrollTop=0});
  const wasOpen=dr.classList.contains('open');
  dr.classList.add('open');document.body.classList.add('dopen');dr.querySelector('.x').focus();
  if(!wasOpen)reflowAfterDrawer();
}
function reflowAfterDrawer(){clearTimeout(reflowAfterDrawer.t);reflowAfterDrawer.t=setTimeout(()=>dispatchEvent(new Event('resize')),240)}
function closeDrawer(){if(!dr.classList.contains('open'))return;dr.classList.remove('open');document.body.classList.remove('dopen');reflowAfterDrawer();if(lastFocus&&document.contains(lastFocus))lastFocus.focus()}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer()});


/* =====================================================================
   ASSET-CLASS TABS: seven self-contained tabs, each with its own tools
   ===================================================================== */
const TABS={
  snapshot:{t:'Snapshot',sub:'Every asset class on one 1–100 scale: the cheapest readings across the board today.',scope:()=>true,
    notes:['market-legends-council-2026-11-23','sector-investing-playbook','sector-rotation-research-evidence','board-backlog']},
  india:{t:'Indian equities',sub:'Three cuts: by market cap (Nifty 50, large, mid and small caps), by sector, and by individual stock (Nifty 50 and your watchlist).',scope:i=>i.id==='NIFTY50'||['sectors','factors','stocks'].includes(i.model),
    notes:['market-legends-council-2026-11-23','watchlist-analysis-2026-11','sector-investing-playbook','india-sector-facts-2016-2026','sector-froth-signals','valuing-cyclical-sectors','sector-rotation-7-indian-bull-runs','flat-markets-are-not-dead-markets','identifying-winning-sectors']},
  global:{t:'International',sub:'The US first, then 20 more markets, all scored for an INR investor over five years.',scope:i=>i.model==='global',
    notes:['sector-rotation-research-evidence','sector-rotation-economic-cycle-schwab']},
  commod:{t:'Commodities',sub:'Gold, silver, Brent crude, copper, aluminium, zinc, iron ore and natural gas.',scope:i=>i.id==='GOLD'||i.model==='commodities',
    notes:['valuing-cyclical-sectors','board-backlog']},
  crypto:{t:'Crypto',sub:'Bitcoin and the four largest coins after it, with the 5% portfolio cap and staging rule.',scope:i=>i.model==='crypto',notes:['board-backlog']},
  fixed:{t:'Fixed income',sub:'Bonds, deposits and cash-like carry, with yields next to scores.',scope:i=>['bonds','carry'].includes(i.model),notes:[]},
  realestate:{t:'Real estate',sub:'Listed REITs and InvITs, and housing by city.',scope:i=>['reits','property'].includes(i.model),notes:[]},
};
/* Tools shown on each tab. The other views (finder, map, alerts, changes, notes) still exist in TOOLVIEW; add them back here to show them. */
const TOOLS=[['','Overview'],['trends','Trends']];
const tabOf=i=>Object.keys(TABS).find(k=>k!=='snapshot'&&TABS[k].scope(i))||'snapshot';
const inTab=t=>ALL_ITEMS.filter(i=>!i.wide&&TABS[t].scope(i));   // headline readings only
const toolOK=(t,k)=>k!=='trends'||t==='snapshot';   // one Trends view, on the Snapshot tab
/* Grid / Table switch for cards that would otherwise show the same readings twice */
const GT={};
const gtSwitch=key=>`<span class="seg gtsw" data-key="${key}" aria-label="Show as">${[['grid','Grid'],['table','Table']].map(([v,l])=>`<button data-v="${v}" class="${(GT[key]||'grid')===v?'on':''}" aria-pressed="${(GT[key]||'grid')===v}">${l}</button>`).join('')}</span>`;

/* ---------- shared visual pieces ---------- */
const tint=(v,p=34)=>v==null?'transparent':`color-mix(in srgb, ${bcol(v)} ${p}%, var(--surface))`;
const fmtPct=(x,d=0)=>x==null?'—':(x>0?'+':'')+(x*100).toFixed(d)+'%';
const ddNow=i=>i&&i.drawdown?i.drawdown.now:null;
const ddTxt=i=>{const d=ddNow(i);return d==null?'—':d>-0.005?'at high':Math.round(d*100)+'%'};
function gauge(s,W=220,lab=false,top=GTOP()){const x=v=>2+(Math.min(v,top)-1)/(top-1)*(W-4);   // top<100 draws only the bands below it (Snapshot: blue bands)
  return `<svg class="gauge" width="${W}" height="${lab?28:16}" viewBox="0 0 ${W} ${lab?28:16}" style="max-width:100%;height:auto" aria-hidden="true">${BANDS.filter(b=>b[1]<top).map(b=>`<rect x="${x(Math.max(1,b[1]))}" y="6" width="${Math.max(1,x(b[2])-x(Math.max(1,b[1]))-1.5)}" height="6" rx="2" fill="var(${b[3]})"/>`).join('')}${s!=null?`<path d="M${x(s)-5},0 L${x(s)+5},0 L${x(s)},6 Z" fill="var(--ink)"/><rect x="${x(s)-1}" y="5" width="2" height="8" fill="var(--ink)"/>`:''}${lab?`<text x="2" y="26">1 cheap</text><text x="${W-2}" y="26" text-anchor="end">${top===100?'100 rich':top+' (top of Accumulate)'}</text>`:''}</svg>`}
function bandMix(list,h=10){const c=BANDS.map(b=>list.filter(i=>bandOf(i.score)===b).length);
  return `<div class="mix" style="height:${h}px" role="img" aria-label="${c.map((n,k)=>BANDS[k][0]+' '+n).join(', ')}">${c.map((n,k)=>n?`<i style="flex:${n};background:var(${BANDS[k][3]})" title="${BANDS[k][0]}: ${n}"></i>`:'').join('')}</div>`}
function hc(v,txt){return `<td class="hc" style="background:${tint(v,40)}">${txt??(v==null?'—':Math.round(v))}</td>`}
function flagIcon(i){const f=[];if(i.flags&&/guard/.test(i.flags))f.push('⚑');else if(i.flags)f.push('<span title="model note" style="color:var(--ink-3)">ⓘ</span>');if(i.parabolic&&i.parabolic.status!=='Normal')f.push('<span class="pill">'+i.parabolic.status+'</span>');return f.join(' ')}
function heatTile(i,sub,v,tip){const val=v===undefined?i.score:v;return `<div class="ht" data-id="${i.id}" role="button" tabindex="0" style="background:${tint(val,46)};border-color:${bcol(val)}" aria-label="${esc(i.name)} ${i.score}${tip?', '+esc(tip):''}"${tip?` title="${esc(i.name)} · ${esc(tip)}"`:''}><div class="htn">${esc(i.name.replace(/^Nifty (India )?/,'').replace(/ Ltd\.?$/,''))}</div><div class="hts"><b>${i.score.toFixed(0)}</b><span>${sub||''}</span></div></div>`}
function areaTile(t,i,label,extra,only){const list=only?inTab(t).filter(only):inTab(t);return `<a class="at" href="#${t}" style="border-top-color:${bcol(i?i.score:null)}"><div class="atl">${TABS[t].t}</div><div class="atv">${i?i.score.toFixed(0):'—'}<span>${i?chip(i.score):''}</span></div><div class="ats">${esc(label)}</div>${gauge(i?i.score:null,180)}${bandMix(list,6)}<div class="ats">${list.length} reading${list.length>1?'s':''}${extra?' · '+extra:''}</div></a>`}
/* sortable table */
const TSORT={};
function sortTable(key,cols,rows,def){const st=TSORT[key]||(TSORT[key]=def||{k:cols[1].k,dir:1});const col=cols.find(c=>c.k===st.k)||cols[0];
  const val=i=>{const v=col.get(i);return v==null||v===''?(st.dir>0?Infinity:-Infinity):v};
  const r=[...rows].sort((a,b)=>{const x=val(a),y=val(b);return (typeof x==='string'?x.localeCompare(y):x-y)*st.dir});
  const keep=new Set((def&&def.keep)||cols.slice(0,3).map(c=>c.k)),mh=c=>keep.has(c.k)?'':' class="mh"';
  const cellOf=(c,i)=>{const h=c.cell?c.cell(i):`<td${c.num?' style="text-align:right"':''}>${c.fmt?c.fmt(i):esc(c.get(i)??'—')}</td>`;return keep.has(c.k)?h:h.startsWith('<td class="')?h.replace('<td class="','<td class="mh '):h.replace('<td','<td class="mh"')};
  return `<div class="tscroll"><table class="st" data-key="${key}"><thead><tr>${cols.map(c=>`<th scope="col"${mh(c)}${c.num?' style="text-align:right"':''}><button class="btn" data-k="${c.k}" aria-sort="${st.k===c.k?(st.dir>0?'ascending':'descending'):'none'}">${c.l}${st.k===c.k?(st.dir>0?' ▲':' ▼'):''}</button></th>`).join('')}</tr></thead><tbody>${r.map(i=>`<tr class="row" data-id="${i.id}" tabindex="0" style="display:table-row">${cols.map(c=>cellOf(c,i)).join('')}</tr>`).join('')}</tbody></table></div>`}
function bindSort(root){root.querySelectorAll('table.st').forEach(t=>t.querySelectorAll('th .btn').forEach(b=>b.onclick=e=>{e.stopPropagation();const st=TSORT[t.dataset.key];st.dir=st.k===b.dataset.k?-st.dir:1;st.k=b.dataset.k;rerender()}))}
const C={name:{k:'name',l:'Name',get:i=>i.name,fmt:i=>`<b>${esc(i.name)}</b>`},
  score:{k:'score',l:'Score',num:1,get:i=>i.score,cell:i=>`<td class="hc sc" title="${bandOf(i.score)[0]}"><span class="sw" style="background:${bcol(i.score)}"></span><b>${i.score.toFixed(1)}</b></td>`},
  band:{k:'band',l:'Band',get:i=>i.score,fmt:i=>chip(i.score)},
  b:(k,l)=>({k:'b_'+k,l:l||k,num:1,get:i=>(i.buckets||{})[k],cell:i=>hc((i.buckets||{})[k])}),
  m:(k,l,num)=>({k:'m_'+k,l:l||k,num,get:i=>{const v=(i.meta||{})[k];return v===''?null:v}}),
  dd:{k:'dd',l:'From high',num:1,get:i=>ddNow(i),fmt:i=>ddTxt(i)},
  flags:{k:'flags',l:'Notes',get:i=>i.flags?1:0,fmt:i=>flagIcon(i)}};

/* ---------- tab overviews ---------- */
let OV_DRAW=[];   // charts drawn after the HTML is in place (and again on resize)
/* Snapshot opens with a heat map of the asset-class model: one tile per asset class, linking to its tab. */
const AC_TAB={'Indian equity':'india','Foreign equity':'global','Indian bonds':'fixed','Foreign bonds':'fixed','Cash':'fixed','Precious metals':'commod','Real estate':'realestate','Crypto':'crypto'};
function acTile(a){const t=AC_TAB[a.family]||'snapshot',tilt=String(a.tilt||'').replace(/\s*\(.*\)$/,'');
  return `<a class="ht" href="#${t}" style="background:${tint(a.score,46)};border-color:${bcol(a.score)};text-decoration:none;color:var(--ink)" aria-label="${esc(a.name)}, score ${a.score}, ${bandOf(a.score)[0]}" title="${esc(a.name)}${a.drivers?' · '+esc(a.drivers):''}">
    <div class="htn">${esc(String(a.name).replace(/\s*\(.*\)$/,''))}</div><div class="hts"><b>${Math.round(a.score)}</b><span>${bandOf(a.score)[0]}</span></div>
    <div class="tag" style="white-space:normal">${esc(tilt)}${a.yield_?` · yield ${a.yield_}%`:''}${a.own!=null?` · full model ${Math.round(a.own)}`:''}</div></a>`}
/* asset class -> the dedicated model's reading, for its worst fall and a click-through */
const AC_ITEM={SHORT_DEBT:'FI_SHORT_1Y',GSEC_LONG:'FI_GSEC_10Y',SILVER:'CMD_SILVER',CREDIT_AA:'FI_CREDIT_AA_3Y',CORP_AAA:'FI_CORP_AAA_5Y',MIDCAP:'SEC_MIDCAP150',NIFTY50:'NIFTY50',GOLD:'GOLD',GLOBAL_EQ:'GLB_ACWI',SMALLCAP:'SEC_SMALLCAP250',US_EQ:'GLB_SP500'};
/* One table to compare asset classes on the same terms: score, yield, the full model's view, how far it has fallen before, and how to buy it. */
function acTable(ac){
  const worst=a=>{const i=byId[AC_ITEM[a.id]];return i&&i.drawdown&&i.drawdown.worst!=null?i.drawdown:null};
  return `<div class="tscroll"><table class="st"><thead><tr><th scope="col">Asset class</th><th scope="col" style="text-align:right">Score</th><th scope="col">Read</th><th scope="col" style="text-align:right">Yield</th><th scope="col" style="text-align:right">Full model</th><th scope="col" style="text-align:right">Worst fall, 10 yrs</th><th scope="col">Model tilt</th><th scope="col">How to buy</th></tr></thead><tbody>
    ${ac.map(a=>{const t=AC_TAB[a.family]||'snapshot',w=worst(a);return `<tr><td><a href="#${t}"><b>${esc(String(a.name).replace(/\s*\(.*\)$/,''))}</b></a></td>${hc(a.score,`<b>${a.score.toFixed(1)}</b>`)}<td>${esc(a.read||'')}</td>
      <td style="text-align:right">${a.yield_?a.yield_+'%':'—'}</td><td style="text-align:right">${(()=>{const i=byId[AC_ITEM[a.id]],v=a.own!=null?a.own:i?i.score:null;return v==null?'—':i?`<a href="#" class="vlink" data-id="${esc(i.id)}">${Math.round(v)}</a>`:Math.round(v)})()}</td>
      <td style="text-align:right" title="${w?'Deepest fall from a high since '+esc(w.window_from||'')+', reached '+esc(w.worst_date||''):'No daily price history (bonds and cash are priced off yields)'}">${w?pct(w.worst):'—'}</td>
      <td>${esc(a.tilt||'')}</td><td style="color:var(--ink-2)">${esc(a.access||'')}</td></tr>`}).join('')}</tbody></table></div>
    <p class="tag" style="margin-top:6px;white-space:normal">Yield: the income the asset-class model credits (earnings yield for equities, rent for housing, none for metals). Full model: the dedicated model's score with timing and macro. Worst fall: the deepest drop from a high in the dedicated model's daily prices over the last ten years.</p>`}
function ovSnapshot(){
  // Blue bands only unless the header switch shows Hold, Trim and Exit too.
  const ac=(DATA.assetClasses||[]).filter(a=>a.score!=null&&inBlue(a.score)).sort((a,b)=>a.score-b.score);
  // each tile: the tab's cheapest investable headline (stocks only if nothing broader qualifies)
  const tile=t=>{const l=inTab(t).filter(investable).sort((a,b)=>a.score-b.score),i=l.find(x=>x.model!=='stocks')||l[0];
    return areaTile(t,i,i?i.name:'None investable today',i&&i.model==='bonds'&&i.meta&&i.meta['Yield %']?`yield ${i.meta['Yield %']}%`:'',investable)};
  OV_DRAW=[];
  return `<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>${SHOW_ALL?'Asset classes':'Investable asset classes'}</h2><p class="hint">${SHOW_ALL?'All asset classes':`Only asset classes in the blue bands (score under ${INVEST_MAX})`}, cheapest first, on the asset-class model (valuation, five-year view). ${GT.ac==='table'?'The table puts them side by side: yield, the full model, worst past fall and how to buy.':'Each tile shows the suggested tilt; "full model" is the dedicated model\'s score with timing and macro added. Switch to Table to compare yield, worst past fall and how to buy.'} Click one to open its tab.</p></div>${gtSwitch('ac')}</div>
    ${!ac.length?'<div class="empty">No asset class is in a blue band today.</div>':GT.ac==='table'?acTable(ac):`<div class="heat ac">${ac.map(acTile).join('')}</div>`}</section>
  <div class="tiles7">${['india','global','commod','crypto','fixed','realestate'].map(tile).join('')}</div>`;
}
/* one-line read at the top of each tab: lean in (≤35) / lean out (>65), from the scores */
const shortName=n=>String(n).replace(/ \(.*\)$/,'').replace(/ Ltd\.?$/,'');
function verdictLine(t){let lin,lout,hold;
  if(t==='snapshot'){const ac=DATA.assetClasses||[];
    lin=ac.filter(a=>/^Overweight/.test(a.tilt||'')).sort((a,b)=>a.score-b.score);lout=ac.filter(a=>/^Underweight/.test(a.tilt||'')).sort((a,b)=>b.score-a.score);hold=ac.length-lin.length-lout.length}
  else{let l=inTab(t).filter(i=>i.score!=null&&!notInvestable(i)&&i.model!=='stocks');
    lin=l.filter(i=>i.score<=35).sort((a,b)=>a.score-b.score);lout=l.filter(i=>i.score>65).sort((a,b)=>b.score-a.score);hold=l.length-lin.length-lout.length}
  if(t==='snapshot'&&!SHOW_ALL){   // blue bands only: no Hold or Lean-out names
    const inv=(DATA.assetClasses||[]).filter(a=>a.score!=null&&a.score<INVEST_MAX).sort((a,b)=>a.score-b.score);
    return `<div class="verdict"><span><b>Investable:</b> ${inv.length?inv.map(a=>esc(shortName(a.name))).join(', '):'nothing in a blue band today'}</span><span class="tag">Asset classes scoring under ${INVEST_MAX} (Strong buy, Buy, Accumulate).</span></div>`}
  const nm=x=>x.slice(0,4).map(i=>byId[i.id]?`<a href="#" data-id="${esc(i.id)}" class="vlink">${esc(shortName(i.name))}</a>`:esc(shortName(i.name))).join(', ')+(x.length>4?` +${x.length-4}`:'');
  if(!SHOW_ALL)return `<div class="verdict"><span><b>Lean in:</b> ${lin.length?nm(lin):'nothing cheap enough'}</span><span class="tag">Lean in = score 35 or lower. Hold, Trim and Exit readings are hidden.</span></div>`;
  return `<div class="verdict"><span><b>Lean in:</b> ${lin.length?nm(lin):'nothing cheap enough'}</span><span><b>Hold:</b> ${hold}</span><span><b>Lean out:</b> ${lout.length?nm(lout):'nothing rich enough'}</span><span class="tag">${t==='snapshot'?'From the asset-class model\'s tilts.':'Lean in = score 35 or lower; lean out = above 65.'}</span></div>`}
let indState={heat:'score',sec:'all',stockView:'grid',uni:'n50',view:'cap',valMax:50,cell:null,dvAll:false};
try{const v=localStorage.getItem('eeb-india-view');indState.view={top:'cap',bottom:'stock'}[v]||(['cap','sector','factor','stock'].includes(v)?v:'cap')}catch(e){}
const SIZE_IDS=['SEC_NIFTY500','SEC_NEXT50','SEC_MIDSELECT','SEC_MIDCAP150','SEC_SMALLCAP250'];
/* value setups (scripts/fetch_parabolic.py price_setup): how a stock's price got where it is */
const SETUPS=[['short','Short-term drawdown','Fell 15% or more from its 3-month high'],['long','Long-term drawdown','30% or more below its 5-year high, and that high is over a year old'],
  ['consol','Consolidation','6 months or more inside a 25% high-to-low band'],['base','Multi-year base','Price has compounded 7% a year or less (about a fixed deposit) for 5 years or more']];
const SETUP_NAME=Object.fromEntries(SETUPS.map(s=>[s[0],s[1]]));
const pc=(x,d=0)=>x==null?'—':(x>0?'+':'')+(x*100).toFixed(d)+'%';
const hasSetup=(i,k)=>!!(i.setup&&i.setup.types&&i.setup.types.includes(k));
function setupNote(i,k){const s=i.setup;if(!s)return '';
  return k==='short'?`${pc(s.dd_3m)} from 3-month high`:k==='long'?`${pc(s.dd_5y)} from 5-yr high (${s.years_below_5y_high} yrs ago)`:
    k==='consol'?`${s.consol_months} months in a ${Math.round(s.consol_range*100)}% band`:`flat ${s.flat_years} yrs · 5-yr price ${pc(s.cagr&&s.cagr['5'],1)}/yr`}
function ovIndia(){
  const v=indState.view;
  const views=[['cap','Market cap','Nifty 50 → large, mid and small caps'],['sector','Sectors','Heat map, table, stock-by-stock check'],['factor','Factors','Value, quality, momentum and low-volatility indices'],['stock','Stocks','Heat map with your watchlist · best value pick per sector']];
  const cur=views.find(x=>x[0]===v)||views[0];
  const sw=`<div class="vbar"><div class="vsw seg" role="tablist" aria-label="Indian equities view">${views.map(([k,t,s])=>`<button role="tab" aria-selected="${v===k}" class="${v===k?'on':''}" data-v="${k}" title="${esc(s)}">${t}</button>`).join('')}</div><span class="tag">${esc(cur[2])}</span></div>`;
  return sw+(v==='cap'?ovIndiaCap():v==='sector'?ovIndiaSector():v==='factor'?ovIndiaFactor():ovStockFocus());
}
const relB=i=>(i.buckets||{})['Relative vs Nifty'];
/* Factors: which investing style is cheap. Grouped by style so the cheapest style reads at a glance. */
const FSTYLES=['Value','Quality','Low volatility','Momentum','Alpha','Equal weight'];
const fStyle=n=>/Low.?Vol/i.test(n)?'Low volatility':/Quality/.test(n)?'Quality':/Momentum/.test(n)?'Momentum':/Value/.test(n)?'Value':/Alpha/.test(n)?'Alpha':/Equal/.test(n)?'Equal weight':'Other';
function ovIndiaFactor(){
  const f=ALL_ITEMS.filter(i=>i.model==='factors'),npe=DATA.size_rotation&&DATA.size_rotation.valuation?DATA.size_rotation.valuation.large.pe:null;
  const pe=i=>(i.meta||{}).PE,b=(i,k)=>(i.buckets||{})[k];
  const tip=i=>[fStyle(i.name),`P/E ${pe(i)??'—'}${npe?` vs Nifty 50 ${npe}`:''}`,`relative to Nifty ${b(i,'Relative vs Nifty')==null?'—':Math.round(b(i,'Relative vs Nifty'))}`,`factor cycle ${b(i,'Factor cycle')==null?'—':Math.round(b(i,'Factor cycle'))}`,`timing ${b(i,'Timing')==null?'—':Math.round(b(i,'Timing'))}`].join(' · ');
  const groups=FSTYLES.concat('Other').map(st=>[st,f.filter(i=>fStyle(i.name)===st).sort((a,c)=>a.score-c.score)]).filter(g=>g[1].length).sort((a,c)=>a[1][0].score-c[1][0].score);
  OV_DRAW=[];
  if(!f.length)return `<div class="empty">No factor index is in a blue band today. ${HIDDEN_NOTE}</div>`;
  const best=groups[0],lead=`Cheapest style today: <b>${esc(best[0])}</b> (${esc(shortName(best[1][0].name))}, ${best[1][0].score.toFixed(0)}).${groups.length>1?` Next: ${groups.slice(1,3).map(g=>`${esc(g[0])} (${g[1][0].score.toFixed(0)})`).join(', ')}.`:''}`;
  if(GT.fac==='table')return tableCard('Factor indices',`${lead} Click a column to sort; click a row for the full panel.`,gtSwitch('fac'),
    sortTable('fac',[C.name,{k:'style',l:'Style',get:i=>fStyle(i.name)},C.score,{k:'rel',l:'Relative',num:1,get:relB,cell:i=>hc(relB(i))},C.b('Valuation'),C.b('Factor cycle','Cycle'),C.b('Timing'),C.b('Filter','Macro'),{k:'pe',l:'P/E',num:1,get:pe,fmt:i=>pe(i)??'—'},C.flags],f,{k:'score',dir:1,keep:['name','score','rel']}));
  return `<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Factor indices by style</h2><p class="hint">${lead} Styles are ordered cheapest first; colour = band. The small figure is the P/E${npe?` (Nifty 50: ${npe})`:''}. Hover a tile for its score relative to the Nifty and its factor-cycle and timing scores; switch to Table to sort them.</p></div>${gtSwitch('fac')}</div>
    ${groups.map(([st,l])=>`<div class="grp">${esc(st)}</div><div class="heat sm">${l.map(i=>heatTile(i,pe(i)!=null?'P/E '+pe(i):'',undefined,tip(i))).join('')}</div>`).join('')}</section>`;
}
/* line chart: series [{name,col,pts:[[label,value],…]}], x = index along the longest series */
function lineChart(id,series,o={}){const el=document.getElementById(id);if(!el||el.clientWidth<80)return;
  const W=el.clientWidth,H=o.H||Math.min(300,Math.max(200,W*.42)),L=48,R=o.R??92,T=12,B=26,n=Math.max(...series.map(s=>s.pts.length));
  const all=series.flatMap(s=>s.pts.map(p=>p[1])).filter(v=>v!=null);let y0=Math.min(...all),y1=Math.max(...all);
  const f=o.log?Math.log:v=>v;if(!o.log){const d=(y1-y0)||1;y0-=d*.06;y1+=d*.06}
  const X=k=>L+k/(n-1)*(W-L-R),Y=v=>T+(f(y1)-f(v))/(f(y1)-f(y0))*(H-T-B);
  let s=`<svg width="${W}" height="${H}" role="img" aria-label="${esc(o.label||'')}">`;
  const ticks=o.ticks||(()=>{const st=(y1-y0)/4;return [0,1,2,3,4].map(k=>y0+st*k)})();
  ticks.filter(v=>v>=y0&&v<=y1).forEach(v=>s+=`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${L-6}" y="${Y(v)+4}" text-anchor="end">${o.yf?o.yf(v):v.toFixed(0)}</text>`);
  if(o.ref!=null&&o.ref>=y0&&o.ref<=y1)s+=`<line x1="${L}" x2="${W-R}" y1="${Y(o.ref)}" y2="${Y(o.ref)}" stroke="var(--ink-3)" stroke-dasharray="4 3"/>`;
  const lab=series[0].pts;let lastY='';lab.forEach((p,k)=>{const y=String(p[0]).slice(0,4);if(y!==lastY&&String(p[0]).slice(5,7)<='01'&&+y%(W<520?6:3)===0){s+=`<text x="${X(k)}" y="${H-8}" text-anchor="middle">${y}</text>`}lastY=y});
  const ends=[];series.forEach(se=>{const d=se.pts.map((p,k)=>p[1]==null?null:`${X(k).toFixed(1)},${Y(p[1]).toFixed(1)}`).filter(Boolean);
    s+=`<polyline points="${d.join(' ')}" fill="none" stroke="${se.col}" stroke-width="${se.w||2}" ${se.dash?'stroke-dasharray="5 4"':''}/>`;
    const lp=se.pts[se.pts.length-1];if(lp&&lp[1]!=null)ends.push({y:Y(lp[1]),t:`${se.name} ${o.ef?o.ef(lp[1]):lp[1].toFixed(0)}`,col:se.col})});
  ends.sort((a,b)=>a.y-b.y);ends.forEach((e,k)=>{if(k&&e.y-ends[k-1].y<13)e.y=ends[k-1].y+13;s+=`<text x="${W-R+6}" y="${e.y+4}" style="fill:${e.col};font-weight:600;font-size:12px">${esc(e.t)}</text>`});
  el.innerHTML=s+'</svg>'}
/* columns for signed values (calendar-year excess) */
function signBars(id,rows,o={}){const el=document.getElementById(id);if(!el||el.clientWidth<80)return;
  const W=el.clientWidth,H=o.H||170,L=36,R=8,T=10,B=22,m=Math.max(1,...rows.map(r=>Math.abs(r[1]||0)));
  const z=T+(H-T-B)/2,sc=(H-T-B)/2/m,bw=(W-L-R)/rows.length;
  let s=`<svg width="${W}" height="${H}" role="img" aria-label="${esc(o.label||'')}"><line x1="${L}" x2="${W-R}" y1="${z}" y2="${z}" stroke="var(--line-2)"/>`;
  [m,-m].forEach(v=>s+=`<text x="${L-6}" y="${z-v*sc+4}" text-anchor="end">${v>0?'+':''}${v.toFixed(0)}</text>`);
  rows.forEach((r,k)=>{const v=r[1]||0,h=Math.abs(v)*sc,x=L+k*bw+2;
    s+=`<rect x="${x.toFixed(1)}" y="${(v>0?z-h:z).toFixed(1)}" width="${Math.max(1,bw-4).toFixed(1)}" height="${Math.max(.5,h).toFixed(1)}" rx="2" fill="${v>=0?'var(--b2)':'var(--b6)'}"><title>${r[0]}: ${v>0?'+':''}${v} pts</title></rect>`;
    if(bw>22||k%2===0)s+=`<text x="${(x+(bw-4)/2).toFixed(1)}" y="${H-6}" text-anchor="middle">${String(r[0]).slice(2)}</text>`});
  el.innerHTML=s+'</svg>'}
const SZC={large:'var(--b1)',mid:'var(--s4)',small:'var(--s1)'};
function splitBar(w,lbl){return `<div class="sbar" role="img" aria-label="${esc(lbl)}: large ${w[0]}%, mid ${w[1]}%, small ${w[2]}%">${['large','mid','small'].map((k,j)=>w[j]>0?`<i style="width:${w[j]}%;background:${SZC[k]}">${w[j]>=9?`${['Large','Mid','Small'][j]} ${Math.round(w[j])}%`:''}</i>`:'').join('')}</div>`}
/* Stocks vs bonds: earnings yield (1/PE) of each size segment against the 10-yr G-sec yield. */
function erpCard(){
  const V=DATA.size_rotation&&DATA.size_rotation.valuation,g=byId.FI_GSEC_10Y,gy=g&&g.meta?+g.meta['Yield %']:null;
  if(!V||!gy)return '';
  const rows=[['Nifty 50',V.large&&V.large.pe],['Midcap 100',V.mid&&V.mid.pe],['Smallcap 100',V.small&&V.small.pe]].filter(r=>r[1]).map(([n,pe])=>({n,pe,ey:100/pe,gap:100/pe-gy}));
  const max=Math.max(gy,...rows.map(r=>r.ey))*1.15,w=v=>(100*v/max).toFixed(1);
  const n=rows[0];
  return `<section class="card" style="margin-bottom:14px"><h2>Stocks against bonds: earnings yield vs the 10-yr G-sec</h2>
    <p class="hint">Earnings yield = 1 ÷ P/E: what each rupee in the index currently earns. The dashed line is the 10-yr government bond yield (${gy.toFixed(2)}%). ${n?`The Nifty 50 earns <b>${n.ey.toFixed(1)}%</b>, ${Math.abs(n.gap).toFixed(1)} points ${n.gap<0?'below':'above'} the G-sec.`:''} The further below the line, the more future earnings growth today's prices already assume.</p>
    ${rows.map(r=>`<div class="hbr" style="cursor:default"><span class="hbn">${esc(r.n)} <span class="tag">P/E ${r.pe}</span></span><span class="hbt" style="position:relative"><i style="width:${w(r.ey)}%;background:var(--b2)"></i><em style="position:absolute;left:${w(gy)}%;top:-3px;bottom:-3px;border-left:2px dashed var(--ink)"></em></span><span class="hbv"><b>${r.ey.toFixed(1)}%</b> <span class="tag">${r.gap>0?'+':''}${r.gap.toFixed(1)} pts</span></span></div>`).join('')}
    <p class="tag" style="margin-top:8px;white-space:normal">In India this gap is usually negative, because company earnings grow with inflation while a bond's coupon is fixed. What matters is the gap against its own history, which the board does not store yet; read today's figure as a level, not a signal.</p></section>`}
function ovIndiaCap(){
  const n=byId.NIFTY50,AM=DATA.amfi,SR=DATA.size_rotation,nShow=n&&inBlue(n.score);
  const size=SIZE_IDS.map(k=>byId[k]).filter(i=>i&&inBlue(i.score));
  const draw=[];
  let rot='';
  if(SR){const B=SR.backtest,V=SR.valuation,sc=v=>v==null?'—':(v>0?'+':'')+v.toFixed(2);
    const pos=v=>Math.max(0,Math.min(100,(v+2)/4*100));
    const pill=v=>v<=-1?'Underweight':v<-0.25?'Lean underweight':v<0.25?'Neutral':v<1?'Lean overweight':'Overweight';
    const PN={A:'Valuation gap vs Nifty',B:'Own-history valuation',C:'Relative momentum',D:'Earnings growth gap',E:'RBI rate cycle'};
    draw.push(()=>lineChart('relc',[{name:'Mid',col:SZC.mid,pts:SR.ratio.map(r=>[r[0],r[1]])},{name:'Small',col:SZC.small,pts:SR.ratio.map(r=>[r[0],r[2]])}],{label:'Midcap 150 and Smallcap 250 total return relative to Nifty 50, rebased to 100 in April 2005',ref:100,R:72}),
      ()=>lineChart('navc',[{name:'Model',col:'var(--b1)',w:2.4,pts:B.nav.map(r=>[r[0],r[1]])},{name:'Fixed',col:'var(--ink-3)',dash:1,pts:B.nav.map(r=>[r[0],r[2]])}],{label:'Growth of one rupee: rotation model versus fixed 55/28/17 split',log:1,ticks:[0.5,1,2,4,8],yf:v=>'₹'+v,ef:v=>'₹'+v.toFixed(1)}),
      ()=>lineChart('wtc',[{name:'Large',col:SZC.large,pts:B.weights.map(r=>[r[0],r[1]])},{name:'Mid',col:SZC.mid,pts:B.weights.map(r=>[r[0],r[2]])},{name:'Small',col:SZC.small,pts:B.weights.map(r=>[r[0],r[3]])}],{label:'Model weights over time',H:180,ticks:[0,25,50,75,100],yf:v=>v+'%',ef:v=>v.toFixed(0)+'%'}),
      ()=>signBars('yrc',B.years,{label:'Model minus fixed split, by calendar year'}));
    rot=`<h3 class="step"><span>2</span>Large, mid or small: the rotation model</h3>
    <div class="grid g2" style="margin-bottom:14px">
      <section class="card"><h2>Where the model stands, ${esc(SR.asof)}</h2>
        <p class="hint">Scores run from −2 (favour large caps) to +2 (favour the smaller segment). Valuation is P/B against the Nifty 50, using each segment's own 10-year history.</p>
        ${['mid','small'].map(k=>`<div class="rotrow"><div class="rotl"><b>${k==='mid'?'Midcaps':'Smallcaps'}</b><span class="tag">${pill(SR.scores[k])}</span></div>
          <div class="rots"><div class="rotbar"><i style="left:${pos(SR.scores[k])}%"></i></div><div class="tag rotax"><span>−2 large</span><span>0</span><span>+2 ${k}</span></div></div><b class="rotv">${sc(SR.scores[k])}</b></div>`).join('')}
        <div class="kv" style="margin-top:10px">${Object.keys(PN).map(p=>`<div>${PN[p]}</div><div>mid ${sc(SR.pillars.mid[p])} · small ${sc(SR.pillars.small[p])}</div>`).join('')}</div>
        <h3 style="margin:14px 0 6px;font-size:14px">Split within equity</h3>
        <div class="tag" style="margin-bottom:4px">Model now (moves a third of the way each month)</div>${splitBar(SR.holding||SR.target,'Model now')}
        <div class="tag" style="margin:8px 0 4px">Where it is heading (full target)</div>${splitBar(SR.target,'Target')}
        <div class="tag" style="margin:8px 0 4px">Strategic base</div>${splitBar(SR.base,'Base')}</section>
      <section class="card"><h2>Why: valuation against history</h2>
        <p class="hint">P/B of the midcap and smallcap proxies compared with the Nifty 50. The model leans against a premium that is far above its norm.</p>
        <div class="tscroll"><table class="st"><thead><tr><th scope="col">Segment</th><th scope="col">P/B</th><th scope="col">P/E</th><th scope="col">P/B vs Nifty now</th><th scope="col">10-yr median</th></tr></thead><tbody>
          <tr><td>Nifty 50</td><td>${V.large.pb}</td><td>${V.large.pe}</td><td>—</td><td>—</td></tr>
          <tr><td>Midcap 100</td><td>${V.mid.pb}</td><td>${V.mid.pe}</td><td><b>${V.mid.pb_premium>0?'+':''}${V.mid.pb_premium}%</b></td><td>${V.mid.pb_premium_med10>0?'+':''}${V.mid.pb_premium_med10}%</td></tr>
          <tr><td>Smallcap 100</td><td>${V.small.pb}</td><td>${V.small.pe}</td><td><b>${V.small.pb_premium>0?'+':''}${V.small.pb_premium}%</b></td><td>${V.small.pb_premium_med10>0?'+':''}${V.small.pb_premium_med10}%</td></tr></tbody></table></div>
        <h3 style="margin:14px 0 4px;font-size:14px">Who has led since 2005</h3>
        <p class="hint">Midcap 150 and Smallcap 250 total return divided by the Nifty 50's, rebased to 100. Rising = the smaller segment is winning.</p><div id="relc"></div></section></div>
    <section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Back-test, ${esc(B.period[0])} to ${esc(B.period[1])}</h2>
      <p class="hint">Rebuilt month by month from NSE data using only what was known at each month-end, against a fixed 55/28/17 split rebalanced monthly. 0.1% cost per unit of turnover; no taxes. The first back-tested model on this board.</p></div>
      <a class="btn" href="${esc(SR.research)}" target="_blank" rel="noopener">Full research and method</a></div>
      <div class="tiles3" style="margin-bottom:12px">
        <div class="at"><div class="atl">Return a year</div><div class="atv">${B.model.cagr}%</div><div class="ats">Fixed split ${B.fixed.cagr}% · Nifty 50 ${B.singles['Nifty 50'].cagr}% · Midcap 150 ${B.singles['Midcap 150'].cagr}%</div></div>
        <div class="at"><div class="atl">Worst fall</div><div class="atv">${B.model.mdd}%</div><div class="ats">Fixed split ${B.fixed.mdd}%. It did not cushion 2008 or 2020.</div></div>
        <div class="at"><div class="atl">Signal strength</div><div class="atv">+${B.corr12.mid}</div><div class="ats">Midcap score vs next-12-month midcap-minus-Nifty return (smallcaps +${B.corr12.small})</div></div></div>
      <div class="grid g2"><div><h3 style="margin:0 0 4px;font-size:14px">Growth of ₹1 (log scale)</h3><div id="navc"></div></div>
        <div><h3 style="margin:0 0 4px;font-size:14px">Model weights</h3><div id="wtc"></div>
          <h3 style="margin:10px 0 4px;font-size:14px">Model minus fixed split, by year (points)</h3><div id="yrc"></div></div></div>
      <div class="tscroll" style="margin-top:10px"><table class="st"><thead><tr><th scope="col">Period</th><th scope="col">Model</th><th scope="col">Fixed split</th><th scope="col">Difference</th><th scope="col">Worst fall, model / fixed</th></tr></thead><tbody>
        ${Object.entries(B.halves).map(([k,h])=>`<tr><td>${k}</td><td>${h.model_cagr}%</td><td>${h.fixed_cagr}%</td><td>${h.excess>0?'+':''}${h.excess} pts</td><td>${h.model_mdd}% / ${h.fixed_mdd}%</td></tr>`).join('')}</tbody></table></div>
      <div class="note" style="margin-top:10px">The valuation signal is real, but turning it into extra return is hard. The model cut small and midcaps before the 2018 top and bought them after the 2009 and 2013 lows, then lagged through the 2021–24 boom while they stayed expensive. Read it as a risk dial that leans against extremes, not a timing engine. ${SR.notes.map(esc).join(' ')}</div></section>`}
  OV_DRAW=draw;
  return `<h3 class="step"><span>1</span>The market and its size bands</h3><div style="margin-bottom:14px">
    ${!nShow?`<section class="card"><h2>Nifty 50</h2><p class="hint">Hidden: the Nifty 50 is not in a blue band today. ${HIDDEN_NOTE}</p></section>`:`<section class="card hero" style="border-top-color:${bcol(n.score)}"><h2>Nifty 50</h2><div class="herorow"><div class="big">${n.score}</div><div>${chip(n.score)}<div class="tag">${esc(n.signal)}</div></div></div>${gauge(n.score,320,true)}
      <div class="bk">${Object.entries(n.buckets).filter(([k,v])=>v!=null).map(([k,v])=>`<div style="background:${tint(v,40)}"><span>${k==='Filter'?'Macro':k}</span><b>${Math.round(v)}</b></div>`).join('')}<div style="background:${tint(ddNow(n)==null?null:50)}"><span>From high</span><b>${ddTxt(n)}</b></div>${AM?`<div style="background:${tint(AM.froth,40)}"><span>Fund froth</span><b>${AM.froth}</b></div>`:''}</div>
      <button class="btn" data-id="NIFTY50" style="margin-top:10px">Open Nifty 50 details</button></section>`}
</div>
  ${erpCard()}
  ${nShow||size.length?heatBlock('Size indices: heat-map','Large to small caps, cheapest first. Colour by score, by score relative to the Nifty 50 (low = cheaper than the market), or by distance from the high.',[...(nShow?[n]:[]),...size],['score','rel','dd']):`<div class="empty" style="margin-bottom:14px">No size index is in a blue band today. ${HIDDEN_NOTE}</div>`}
  ${rot}`;
}
/* Heat-map block shared by the Market cap, Sectors and Stocks views. modes: which "colour by" options to offer. */
const HEAT_MODES={score:['Score',i=>i.score,i=>chip(i.score).replace(/<span class="sw"[^>]*><\/span>/,'')],
  rel:['Relative to Nifty',relB,i=>'rel '+(relB(i)==null?'—':Math.round(relB(i)))],
  val:['Valuation',i=>(i.buckets||{}).Valuation,i=>'val '+((i.buckets||{}).Valuation==null?'—':Math.round((i.buckets||{}).Valuation))],
  dd:['Distance from high',i=>{const d=ddNow(i);return d==null?null:Math.max(1,Math.min(100,100+d*200))},i=>ddTxt(i)]};
function heatBlock(title,hint,list,modes,o={}){
  const m=modes.includes(indState.heat)?indState.heat:modes[0],[,hv,hsub]=HEAT_MODES[m];
  const l=[...list].sort((a,b)=>(hv(a)??999)-(hv(b)??999));
  return `<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>${title}</h2><p class="hint">${hint}</p></div>
    <div class="filters" style="margin:0">${modes.length>1?`<span class="seg heatseg" aria-label="Colour by">${modes.map(k=>`<button data-v="${k}" class="${k===m?'on':''}">${HEAT_MODES[k][0]}</button>`).join('')}</span>`:''}${o.sw||''}</div></div>
    <div class="heat${o.cls?' '+o.cls:''}">${l.map(i=>heatTile(i,(o.star&&i.watch?'★ ':'')+(o.sub?o.sub(i):hsub(i))+(i.flags&&/guard/.test(i.flags)?' ⚑':''),hv(i),o.tip?o.tip(i):'')).join('')}</div>
    ${m==='dd'?'<div class="tag" style="margin-top:6px">Distance from high: blue = far below its 10-year high, red = at or near it. Grey tiles have no daily price history.</div>':''}</section>`}
function tableCard(title,hint,sw,table){return `<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>${title}</h2><p class="hint">${hint}</p></div>${sw}</div>${table}</section>`}
function ovIndiaSector(){
  const sectors=ALL_ITEMS.filter(i=>i.model==='sectors'&&!SIZE_IDS.includes(i.id));
  OV_DRAW=[];
  return `${GT.sec==='table'?tableCard('Sectors','Click a column to sort; click a row for the full panel. ⚑ = peak-earnings guard on; ⓘ = model note.',gtSwitch('sec'),
      sortTable('sec',[C.name,C.score,{k:'rel',l:'Relative',num:1,get:relB,cell:i=>hc(relB(i))},C.b('Valuation'),C.b('Sector cycle','Cycle'),C.b('Timing'),C.b('Filter','Macro'),C.dd,C.flags],sectors,{k:'score',dir:1,keep:['name','score','rel']}))
    :heatBlock('Sectors','Cheapest to richest. Colour shows the band of what you colour by. Switch to Table for the valuation, cycle, timing and macro scores.',sectors,['score','rel','dd'],{sw:gtSwitch('sec')})}
  <h3 class="step">Hand-off to stocks</h3>
  <section class="card"><h2>Does the sector call hold stock by stock?</h2><p class="hint">Big dot: the sector index's score. Small dots: its Nifty 50 and watchlist stocks. Diamond: their median. Right-hand column: <b>gap</b> = stock median minus the index score (negative: the stocks are cheaper than the index suggests; ⚑ when 10 or more points apart) · <b>spread</b> = richest stock minus cheapest (wide: pick stocks, don't buy the whole sector). Sectors with the biggest gap come first. Open the Stocks view for the names.</p><div id="sxsvg"></div></section>`;
}
/* Value picks: Nifty 50 only, score 50 or lower, at least one price setup, no falling-knife veto.
   Best one per NSE sector; a second only when it scores PICK_SECOND or lower. Capped at PICK_MAX. */
const PICK_MAX=20,PICK_SECOND=25;
function valuePicks(all){
  const IN=i=>i.meta.Industry||i.meta.Sector;
  const ok=all.filter(i=>i.meta.Universe==='Nifty 50'&&i.score<=50&&i.setup&&(i.setup.types||[]).length&&!/^BUY VETOED/.test(i.signal||'')).sort((a,b)=>a.score-b.score);
  const n={},out=[];
  ok.forEach(i=>{const s=IN(i),k=n[s]||0;if(k===0||(k===1&&i.score<=PICK_SECOND)){out.push(i);n[s]=k+1}});
  return out.slice(0,PICK_MAX);
}
function ovStockFocus(){
  const all=ALL_ITEMS.filter(i=>i.model==='stocks'&&i.score!=null);
  const watch=ALL_ITEMS.filter(i=>i.watch).sort((a,b)=>(a.score??999)-(b.score??999));
  const watchMissing=(DATA.watchlist||[]).filter(w=>!byId['STK_'+w.ticker]);
  const IN=i=>i.meta.Industry||i.meta.Sector;
  const picks=valuePicks(all);
  const nm=i=>`${i.watch?'★ ':''}<b>${esc(i.name.replace(/ Ltd\.?$/,''))}</b>`;
  const pe={k:'pe',l:'P/E vs sector',num:1,get:i=>i.meta.PE,fmt:i=>`${i.meta.PE??'—'} <span class="tag">/ ${i.meta['Sector PE']??'—'}</span>`};
  const eps={k:'eps',l:'EPS growth',num:1,get:i=>(i.growth||{}).eps_cagr,fmt:i=>{const g=i.growth||{};return g.eps_cagr==null?'—':(g.eps_cagr>0?'+':'')+g.eps_cagr+'%/yr'}};
  const why={k:'why',l:'Why it is cheap now',get:i=>i.setup?i.setup.types.length:0,fmt:i=>i.setup&&i.setup.types.length?i.setup.types.map(t=>`<span class="pill sp" title="${esc(setupNote(i,t))}">${SETUP_NAME[t]}</span>`).join(' '):'—'};
  const asof=all.find(i=>i.setup&&i.setup.asof);
  const short=all.filter(i=>hasSetup(i,'short')&&!/^BUY VETOED/.test(i.signal||'')).sort((a,b)=>a.score-b.score).slice(0,10);
  // the watchlist table's details now ride on each heat-map tile (hover, or the screen-reader label)
  const tip=i=>{const g=i.growth||{},m=i.meta||{};return [IN(i),`score ${i.score.toFixed(1)}`,`P/E ${m.PE??'—'} vs sector ${m['Sector PE']??'—'}`,
    `EPS growth ${g.eps_cagr==null?'—':(g.eps_cagr>0?'+':'')+g.eps_cagr+'%/yr'}`,`ROE 5-yr ${g.roe5!=null?g.roe5+'%':'—'}`,
    `from 3-mo high ${i.setup?pc(i.setup.dd_3m):'—'}`,i.setup&&i.setup.types.length?'cheap now: '+i.setup.types.map(t=>SETUP_NAME[t]).join(', '):''].filter(Boolean).join(' · ')};
  return `${heatBlock('Nifty 50 and watchlist: heat-map',`Every stock on the board, cheapest first. ★ = on your watchlist (${watch.length} shown). Hover a tile for sector, P/E vs sector, EPS growth, 5-year ROE, distance from the 3-month high and why it is cheap; click it for the full panel.${watchMissing.length?` Watchlist names not scored yet: ${watchMissing.map(w=>esc(w.name)).join(', ')}.`:''}`,all,['score','val','dd'],{cls:'sm',star:1,tip})}
  <h3 class="step">Value opportunities: the best in each sector</h3>
  <section class="card"><p class="hint">From the Nifty 50: stocks scoring 50 or lower that show a value setup now, best one per sector (a second only if it scores ${PICK_SECOND} or lower), cheapest first. Falling knives the model vetoes are left out. Hover a setup for the detail.${asof?` Prices to ${esc(String(asof.setup.asof).slice(0,10))}.`:''}</p>
    ${picks.length?sortTable('vp',[{k:'name',l:'Name',get:i=>i.name,fmt:nm},{k:'ind',l:'Sector',get:IN},C.score,pe,eps,why],picks,{k:'score',dir:1,keep:['name','score','why']})
      :'<div class="empty">The value setups come from the daily price check and appear after its next run.</div>'}
    ${short.length?`<details style="margin-top:10px"><summary class="tag xnote">Note: top 10 on short-term reasons (fell 15%+ from the 3-month high)</summary><div class="tag" style="white-space:normal;margin-top:6px">${short.map((i,k)=>`${k+1}. ${esc(i.name.replace(/ Ltd\.?$/,''))} (${i.score.toFixed(0)}, ${pc(i.setup.dd_3m)})`).join(' · ')}</div></details>`:''}</section>`;
}
const REGION={'United States':'Americas',Canada:'Americas',Brazil:'Americas',Mexico:'Americas','United Kingdom':'Europe',France:'Europe',Germany:'Europe',Netherlands:'Europe',Italy:'Europe',Spain:'Europe',Poland:'Europe',Turkey:'Europe & Middle East',Russia:'Europe & Middle East','Saudi Arabia':'Europe & Middle East',Japan:'Asia-Pacific',Australia:'Asia-Pacific','South Korea':'Asia-Pacific',China:'Asia-Pacific',India:'Asia-Pacific',Indonesia:'Asia-Pacific',World:'World'};
function ovGlobal(){
  const g=ALL_ITEMS.filter(i=>i.model==='global');
  const er=i=>{const v=(i.meta||{})['Exp. INR return % p.a. (net)'];return v===''||v==null?null:+v};
  const regions=['Americas','Europe','Europe & Middle East','Asia-Pacific','World'].map(r=>[r,g.filter(i=>(REGION[i.meta.Economy]||'Asia-Pacific')===r).sort((a,b)=>a.score-b.score)]).filter(r=>r[1].length);
  OV_DRAW=[];
  const tip=i=>[i.meta.Economy,`expected ${er(i)==null?'—':er(i)+'%'} a year in INR${i.meta.Range?' ('+i.meta.Range+')':''}`,i.meta.Access?'how to buy: '+i.meta.Access:'',i.action||'',`from high ${ddTxt(i)}`].filter(Boolean).join(' · ');
  const acc=i=>String(i.meta.Access||''),route_=i=>/^Not investable/i.test(acc(i))?'Not investable':/NSE/.test(acc(i))?'NSE-listed':/LRS/.test(acc(i))?'Overseas (LRS)':acc(i)?'Other':'—';
  if(GT.glb==='table')return tableCard('Markets','Click a column to sort. Expected return is net, in INR, a year over five years.',gtSwitch('glb'),
    sortTable('glb',[C.m('Economy'),C.name,C.score,C.b('Valuation'),C.b('Macro'),C.b('Currency'),C.b('Timing'),{k:'er',l:'Exp. INR %/yr',num:1,get:er,fmt:i=>er(i)==null?'—':er(i).toFixed(1)},C.dd,{k:'acc',l:'How to buy',get:acc,fmt:i=>`<span title="${esc(acc(i))}">${esc(route_(i))}</span>`}],g,{k:'score',dir:1,keep:['m_Economy','name','score','er','acc']}));
  return `<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Markets by region</h2><p class="hint">Cheapest first within each region. Colour = band; the small figure is the expected return a year in INR over five years. Hover a tile for its range, the model's action and distance from high; click it to open it. Switch to Table for the valuation, macro, currency and timing scores.</p></div>${gtSwitch('glb')}</div>${regions.map(([r,l])=>`<div class="grp">${r}</div><div class="heat sm">${l.map(i=>heatTile(i,(er(i)!=null?er(i)+'%/yr':'')+(route_(i)==='NSE-listed'?' · NSE':route_(i)==='Overseas (LRS)'?' · LRS':''),undefined,tip(i))).join('')}</div>`).join('')}
    <div class="tag" style="margin-top:6px;white-space:normal">NSE = an India-listed ETF or fund exists; LRS = only through the overseas remittance route (TCS and foreign-asset reporting apply). Hover a tile for the exact route.</div></section>`;
}
const PKEY={GOLD:'gold_usd',CMD_SILVER:'silver_usd',CMD_BRENT:'brent_usd',CMD_COPPER:'copper_usd_t',BTC:'btc_usd'};
function priceLine(i){const k=PKEY[i.id];if(!k)return '';const run=(DATA.run_prices||{})[k],lp=latestPrice(k);if(!run||!lp)return '';const ch=lp.value/run-1;
  return `<div class="kv"><div>Price at scoring</div><div>${(+run).toLocaleString('en-IN')} ${PRICE_META[k][1]}</div><div>Latest</div><div>${(+lp.value).toLocaleString('en-IN',{maximumFractionDigits:2})} <b>${fmtPct(ch,1)}</b>${Math.abs(ch)>=.05?' <span class="stat due">big move</span>':''}</div></div>`}
/* "Linked to" names the Indian sector index and stocks a commodity drives; show their scores so a cheap commodity points to an equity idea. */
function linkFind(nm){const q=nm.trim().toLowerCase();if(!q)return null;
  const c=DATA.items.filter(x=>x.score!=null&&(x.model==='sectors'||x.model==='stocks')&&(x.name.toLowerCase()===q||x.name.toLowerCase().startsWith(q+' ')||x.name.toLowerCase().startsWith(q+'.')||(x.model==='stocks'&&x.name.toLowerCase().startsWith(q))));
  return c.sort((a,b)=>(a.model==='sectors'?0:1)-(b.model==='sectors'?0:1)||a.name.length-b.name.length)[0]||null}
function linkedBlock(i){const raw=(i.meta||{})['Linked to'];if(!raw)return '';
  const names=raw.split(/[;,]/).map(x=>x.trim()).filter(Boolean),found=names.map(n=>[n,linkFind(n)]);
  const shown=found.filter(([,x])=>x&&inBlue(x.score)),hidden=found.filter(([,x])=>x&&!inBlue(x.score)).length,plain=found.filter(([,x])=>!x).map(([n])=>n);
  return `<div class="note" style="margin-top:8px"><b>In Indian equities:</b> ${shown.length?shown.map(([,x])=>`<a href="#" class="vlink" data-id="${esc(x.id)}"><span class="sw" style="background:${bcol(x.score)}"></span>${esc(shortName(x.name))} ${x.score.toFixed(0)}</a>`).join(' · '):'none in a blue band'}${hidden?` <span class="tag">+${hidden} not in a blue band</span>`:''}${plain.length?` <span class="tag">Also: ${esc(plain.join(', '))}</span>`:''}</div>`}
function assetCard(i,wide){const P=i.parabolic;return `<section class="card hero" style="border-top-color:${bcol(i.score)}"><div class="cardhead"><h2>${esc(i.name)}</h2>${tierTag(i.tier)}</div>
  <div class="herorow"><div class="big">${i.score}</div><div>${chip(i.score)}<div class="tag">${esc(i.signal)}</div></div></div>${gauge(i.score,wide?420:280,true)}
  <div class="bk">${Object.entries(i.buckets||{}).filter(([k,v])=>v!=null).map(([k,v])=>`<div style="background:${tint(v,40)}"><span>${k==='Filter'?'Macro':k}</span><b>${Math.round(v)}</b></div>`).join('')}
   <div style="background:${tint(ddNow(i)==null?null:Math.max(1,Math.min(100,100+ddNow(i)*200)),30)}"><span>From high</span><b>${ddTxt(i)}</b></div>${P?`<div style="background:${tint(Math.max(1,Math.min(100,50+P.gap*70)),30)}"><span>vs 150-day avg</span><b>${fmtPct(P.gap)}</b></div>`:''}</div>
  ${i.history&&i.history.length>2?`<div class="tag" style="margin-top:8px">Score, last ${Math.min(24,i.history.length)} months</div>${spark(i.history.slice(-24),wide?560:300,wide?110:60)}`:''}
  ${priceLine(i)}${i.action?`<div class="note"><b>Model's action:</b> ${esc(i.action)}</div>`:''}${linkedBlock(i)}
  <button class="btn" data-id="${i.id}" style="margin-top:8px">Open full details</button></section>`}
function ovCommod(){const l=['GOLD','CMD_SILVER','CMD_BRENT','CMD_COPPER','CMD_ALUMINIUM','CMD_ZINC','CMD_IRONORE','CMD_NATGAS'].map(k=>byId[k]).filter(i=>i&&i.score!=null&&inBlue(i.score));
  OV_DRAW=[];
  return `${SHOW_ALL?'':`<p class="hint" style="margin-bottom:10px">${HIDDEN_NOTE}</p>`}<div class="grid g2">${l.map(i=>assetCard(i)).join('')}</div>`}
function ovCrypto(){const b=byId.BTC,coins=ALL_ITEMS.filter(i=>i.model==='crypto');
  return `<div class="grid g2" style="margin-bottom:14px"><div>${inBlue(b.score)?assetCard(b,true):`<section class="card"><h2>Bitcoin</h2><p class="hint">Hidden: Bitcoin is not in a blue band today. ${HIDDEN_NOTE}</p></section>`}</div><section class="card"><h2>Rules that come with it</h2>
  <ul class="rules"><li><b>Cap all crypto together at 5% of the portfolio.</b> Bitcoin's falls have reached ${b.drawdown?pct(b.drawdown.worst):'−80%'} in the last decade; the other coins fall further.</li><li><b>Stage entries</b> when the macro filter is high (now ${b.buckets.Filter}).</li><li><b>Tax:</b> 31.2% on gains (VDA), no loss set-off.</li><li>Score history before Nov 2026 is reconstructed for Bitcoin (±3 points).</li></ul>
  <div class="tag" style="margin-top:8px">Bitcoin's distance from high</div>${b.drawdown?`<div class="ddbar"><i style="width:${Math.min(100,-b.drawdown.now*100)}%"></i></div><div class="tag">${pct(b.drawdown.now)} from its ${b.drawdown.high_date} high · worst ${pct(b.drawdown.worst)} (${b.drawdown.worst_date})</div>`:''}</section></div>
  <section class="card"><h2>All coins</h2><p class="hint">Bitcoin and the four largest coins after it (stablecoins excluded). Only Bitcoin has a full model; the others are price-and-cycle readings with Bitcoin's macro filter. Click a column to sort; click a row for the full panel.</p>${sortTable('cry',[C.name,C.score,C.b('Valuation'),C.b('Timing'),C.b('Filter','Macro'),C.dd],coins,{k:'score',dir:1,keep:['name','score','dd']})}</section>`}
/* Yields by tenor and credit, from the bond model's own inputs (market data, so every instrument is plotted). */
const FI_TENOR={FI_SHORT_1Y:[1,'1-yr AAA / CD','c'],FI_CREDIT_AA_3Y:[3,'AA credit 3-yr','c'],FI_GSEC_5Y:[5,'G-sec 5-yr','g'],FI_CORP_AAA_5Y:[5,'AAA 5-yr','c'],FI_BANK_FD_5Y:[5,'Bank FD 5-yr','d'],FI_FRSB:[7,'RBI FRSB 7-yr','g'],FI_GSEC_10Y:[10,'G-sec 10-yr','g']};
function yieldCurve(){
  const pts=Object.entries(FI_TENOR).map(([id,[t,l,k]])=>{const i=byId[id],y=i&&i.meta?+i.meta['Yield %']:NaN;return isNaN(y)?null:{id,t,l,k,y}}).filter(Boolean);
  if(pts.length<3)return '';
  const W=640,H=250,L=44,R=120,T=14,B=34,ys=pts.map(p=>p.y),y0=Math.floor((Math.min(...ys)-.3)*2)/2,y1=Math.ceil((Math.max(...ys)+.3)*2)/2;
  const X=t=>L+t/11*(W-L-R),Y=v=>T+(y1-v)/(y1-y0)*(H-T-B),g=id=>(pts.find(p=>p.id===id)||{}).y;
  let s=`<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;max-width:760px" role="img" aria-label="Yields by tenor: ${pts.map(p=>p.l+' '+p.y+'%').join(', ')}">`;
  for(let v=y0;v<=y1+1e-9;v+=.5)s+=`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${L-6}" y="${Y(v)+4}" text-anchor="end">${v.toFixed(1)}%</text>`;
  [0,1,3,5,7,10].forEach(t=>s+=`<text x="${X(t)}" y="${H-B+16}" text-anchor="middle">${t}y</text>`);
  s+=`<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">Tenor (years)</text>`;
  const line=(ids,dash)=>{const q=ids.map(id=>pts.find(p=>p.id===id)).filter(Boolean);if(q.length>1)s+=`<path d="${q.map((p,k)=>(k?'L':'M')+X(p.t)+','+Y(p.y)).join('')}" fill="none" stroke="var(--ink-2)" stroke-width="1.6" ${dash?'stroke-dasharray="5 4"':''}/>`};
  line(['FI_GSEC_5Y','FI_GSEC_10Y']);line(['FI_SHORT_1Y','FI_CREDIT_AA_3Y','FI_CORP_AAA_5Y'],1);
  pts.forEach(p=>{const fill=p.k==='g'?'var(--ink)':p.k==='d'?'var(--surface)':'var(--ink-3)';
    s+=`<circle cx="${X(p.t)}" cy="${Y(p.y)}" r="5" fill="${fill}" stroke="var(--ink)" stroke-width="1.5"/><text x="${X(p.t)+9}" y="${Y(p.y)+4}" style="fill:var(--ink);font-size:12px;paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round">${esc(p.l)} ${p.y.toFixed(2)}%</text>`});
  s+='</svg>';
  const sp=[['AAA 5-yr over G-sec 5-yr','FI_CORP_AAA_5Y','FI_GSEC_5Y','the extra yield for top-rated corporate credit'],
    ['AA 3-yr over G-sec 5-yr','FI_CREDIT_AA_3Y','FI_GSEC_5Y','pay for default and liquidity risk (tenors differ)'],
    ['Bank FD 5-yr over G-sec 5-yr','FI_BANK_FD_5Y','FI_GSEC_5Y','negative = a gilt fund pays more than the FD, before tax'],
    ['1-yr AAA / CD over G-sec 10-yr','FI_SHORT_1Y','FI_GSEC_10Y','positive = the short end pays more than the long end, so extending duration earns nothing extra today']]
    .filter(r=>g(r[1])!=null&&g(r[2])!=null).map(r=>[r[0],g(r[1])-g(r[2]),r[3]]);
  return `<section class="card" style="margin-bottom:14px"><h2>Yield curve and spreads</h2><p class="hint">Every instrument the bond model scores, by tenor. Solid line: government bonds. Dashed: corporate credit. Hollow dot: bank FD. Yields are pre-tax.</p>${s}
    <div class="kv" style="margin-top:8px">${sp.map(([l,v,n])=>`<div>${esc(l)}</div><div><b>${v>0?'+':''}${v.toFixed(2)} pts</b> <span class="tag" style="white-space:normal">${esc(n)}</span></div>`).join('')}</div></section>`}
function ovFixed(){const bonds=ALL_ITEMS.filter(i=>i.model==='bonds'),carry=ALL_ITEMS.filter(i=>i.model==='carry');
  const y=i=>+((i.meta||{})['Yield %']||0);
  return `${yieldCurve()}<section class="card" style="margin-bottom:14px"><h2>Bonds and deposits</h2>${sortTable('fi',[C.name,C.score,{k:'y',l:'Yield %',num:1,get:y,fmt:i=>y(i).toFixed(2)},C.b('Valuation'),C.b('Timing'),C.b('Filter','Macro'),{k:'act',l:"Model's action",get:i=>i.action||''},{k:'acc',l:'How to buy',get:i=>(i.meta||{}).Access||'',fmt:i=>`<span style="color:var(--ink-2)">${esc((i.meta||{}).Access||'—')}</span>`}],bonds,{k:'score',dir:1,keep:['name','score','y']})}</section>
  <section class="card"><h2>Cash-like carry</h2><div class="grid g2">${carry.map(i=>`<div class="at" data-id="${i.id}" role="button" tabindex="0" style="border-top-color:${bcol(i.score)}"><div class="atl">${esc(i.name)}</div><div class="atv">${i.score.toFixed(0)}<span>${chip(i.score)}</span></div>${gauge(i.score,200)}<div class="ats">Post-tax ${esc(i.meta['Post-tax yield %'])}% · edge vs liquid ${esc(i.meta['Edge vs liquid (pp)'])} pp</div><div class="ats">${esc(i.action||'')}</div></div>`).join('')}</div></section>`}
function ovRE(){const r=ALL_ITEMS.filter(i=>i.model==='reits'),c=ALL_ITEMS.filter(i=>i.model==='property');const m=(i,k)=>{const v=(i.meta||{})[k];return v===''||v==null?null:+v};
  OV_DRAW=[];
  return `${GT.re!=='table'?heatBlock('Listed REITs and InvITs','Cheapest to richest. The small figure is the post-tax distribution yield. Switch to Table for yield, spread over the G-sec and price-to-NAV. Click a tile for the full panel.',r,['score','dd'],{sub:i=>m(i,'Post-tax yield %')!=null?`${m(i,'Post-tax yield %')}% post-tax`:'—',sw:gtSwitch('re')})
    :tableCard('Listed REITs and InvITs','Click a column to sort; click a row for the full panel.',gtSwitch('re'),sortTable('re',[C.name,C.m('Type'),C.score,{k:'y',l:'Yield %',num:1,get:i=>m(i,'Distribution yield %'),fmt:i=>m(i,'Distribution yield %')??'—'},{k:'pty',l:'Post-tax %',num:1,get:i=>m(i,'Post-tax yield %'),fmt:i=>m(i,'Post-tax yield %')??'—'},{k:'sp',l:'Spread vs G-sec',num:1,get:i=>m(i,'Spread vs G-sec (pp)'),fmt:i=>m(i,'Spread vs G-sec (pp)')??'—'},{k:'pn',l:'P/NAV',num:1,get:i=>m(i,'Price/NAV'),fmt:i=>m(i,'Price/NAV')??'—'},C.dd],r,{k:'score',dir:1,keep:['name','score','pty']}))}
  <section class="card"><h2>Housing by city</h2><p class="hint">Valuation only; colour = band. Use the rent-vs-buy calculator on your own numbers.</p><div class="heat">${c.sort((a,b)=>a.score-b.score).map(i=>heatTile(i,`rent ${m(i,'Rent yield %')}%`)).join('')}</div></section>`}
const OVERVIEW={snapshot:ovSnapshot,india:ovIndia,global:ovGlobal,commod:ovCommod,crypto:ovCrypto,fixed:ovFixed,realestate:ovRE};

function viewHealth(){return `<div class="card"><h2>Data health</h2><p class="hint">Live prices against the prices each model was scored at, and how fresh each model's inputs are.</p></div>${healthHTML()}`}

/* ---------- per-item tools in the side panel ---------- */
const _openDrawer=openDrawer;
openDrawer=function(id){_openDrawer(id);const i=byId[id];if(!i)return;const t=tabOf(i);
  const tools=[];
  if(i.history&&i.history.length>1)tools.unshift([`#snapshot/trends`,'Trend',()=>{SERIES_ALL.forEach(([k])=>trendState.on[k]=k===i.id?1:0)}]);
  if(!tools.length)return;
  const bar=document.createElement('div');bar.className='dtools';bar.innerHTML=`<span class="tag">Open in ${TABS[t].t}:</span>`+tools.map((x,k)=>`<a class="btn" href="${x[0]}" data-k="${k}">${x[1]}</a>`).join('');
  bar.querySelectorAll('a').forEach(a=>a.onclick=()=>{const f=tools[+a.dataset.k][2];if(f)f();closeDrawer()});
  const h=dr.querySelector('.dtabs')||dr.querySelector('#drh');h.insertAdjacentElement('beforebegin',bar)};

/* ---------- router ---------- */
const LEGACY={month:'snapshot',signals:'snapshot',map:'snapshot',classes:'snapshot',trends:'snapshot/trends',alerts:'snapshot'};
const TOOLVIEW={trends:[viewTrends,bindTrends]};
let CUR={tab:'snapshot',tool:''};
function rerender(){route()}
function route(){
  let h=(location.hash||'#snapshot').slice(1);
  if(LEGACY[h.split('/')[0]]&&!TABS[h.split('/')[0]]){history.replaceState(null,'','#'+LEGACY[h.split('/')[0]]);h=LEGACY[h.split('/')[0]]}
  const [a,b]=h.split('/');const m=document.getElementById('view');hideTT();
  document.querySelectorAll('#nav a').forEach(x=>x.classList.toggle('on',x.getAttribute('href')==='#'+(TABS[a]?a:'')));
  OV_DRAW=[];
  if(a==='knowledge'||a==='notes'||a==='health'){items=ALL_ITEMS;CUR={tab:a,tool:''};
    m.innerHTML=a==='knowledge'?viewKnowledge():a==='notes'?viewNotes():viewHealth();bindRows(m);if(a==='knowledge')drawKnowledge();return}
  const t=TABS[a]?a:'snapshot',tool=TOOLVIEW[b]&&TOOLS.some(x=>x[0]===b)&&toolOK(t,b)?b:'';CUR={tab:t,tool};
  items=ALL_ITEMS.filter(TABS[t].scope);
  const tl=TOOLS.filter(([k])=>!k||toolOK(t,k));   // a bar with only "Overview" in it is left out
  const bar=`<div class="tabhead"><div><h1 class="tabt">${TABS[t].t}</h1><p class="tabs">${TABS[t].sub}</p></div></div>
    ${tl.length>1?`<div class="tbar" aria-label="Views for ${TABS[t].t}">${tl.map(([k,l])=>`<a class="${k===tool?'on':''}" href="#${t}${k?'/'+k:''}" aria-current="${k===tool?'page':'false'}">${l}</a>`).join('')}</div>`:''}
    ${!tool&&t!=='snapshot'?verdictLine(t):''}`;
  let body,after=null;
  if(!tool){body=OVERVIEW[t]();after=()=>{OV_DRAW.forEach(f=>f());if(t==='india')drawSX()}}
  else{body=TOOLVIEW[tool][0]();after=TOOLVIEW[tool][1]}
  m.innerHTML=bar+`<div class="tabbody">${body}</div>`;bindRows(m);bindSort(m);
  m.querySelectorAll('.vlink').forEach(x=>x.onclick=e=>{e.preventDefault();openDrawer(x.dataset.id)});
  m.querySelectorAll('.at[href]').forEach(x=>x.onclick=null);
  if(after)after();
  m.querySelectorAll('.heatseg button').forEach(x=>{x.onclick=()=>{indState.heat=x.dataset.v;rerender()}});
  m.querySelectorAll('.gtsw button').forEach(x=>{x.onclick=()=>{GT[x.parentElement.dataset.key]=x.dataset.v;rerender()}});
  if(t==='india'&&!tool)m.querySelectorAll('.vsw button').forEach(x=>x.onclick=()=>{indState.view=x.dataset.v;try{localStorage.setItem('eeb-india-view',x.dataset.v)}catch(e){}rerender()});
}
addEventListener('hashchange',()=>{route();window.scrollTo(0,0)});
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>{if(!CUR.tool&&TABS[CUR.tab]){OV_DRAW.forEach(f=>f());if(CUR.tab==='india')drawSX()}else if(CUR.tool==='trends')drawTrends()},150)});
freshLine();route();fetchLive();
