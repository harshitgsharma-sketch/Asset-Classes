const DATA = window.__DATA__;
/* ---------- FRESHNESS + LIVE PRICES (recomputed on every load) ---------- */
const TODAY=new Date();
const MONTHNAME=(()=>{const d=Object.values(DATA.models||{}).map(m=>m.asof).filter(Boolean).sort().pop();return d?new Date(d+'T00:00:00').toLocaleString('en-IN',{month:'long'}):'Monthly'})();
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
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const bandOf=s=>s==null?null:BANDS.find(b=>s<=b[2])||BANDS[5];
const bcol=s=>{const b=bandOf(s);return b?`var(${b[3]})`:'var(--line-2)'};
/* Stock universe on the board: the Nifty 50 plus the watchlist. The pipeline still scores the
   whole Nifty 500; set STOCK_UNIVERSE to 'nifty500' to show those stocks again. */
const STOCK_UNIVERSE='nifty50';
const ALL_ITEMS=DATA.items.filter(i=>i.score!=null&&!(STOCK_UNIVERSE==='nifty50'&&i.model==='stocks'&&i.meta&&i.meta.Universe==='Nifty 500'&&!i.watch));
let items=ALL_ITEMS;   // narrowed to the open tab's scope by the router
/* Nifty 500 stocks outside the Nifty 50 are on the map, list, search and sector chart, but kept out of the headline counts and signal lanes so 450 stocks do not swamp the other models. */
ALL_ITEMS.forEach(i=>{i.wide=i.model==='stocks'&&(i.meta||{}).Universe!=='Nifty 50'});
const HL=()=>items.filter(i=>!i.wide);
const byId=Object.fromEntries(DATA.items.map(i=>[i.id,i]));
const pct=x=>Math.round(x*100)+'%';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const notInvestable=i=>/Not investable/i.test(i.action||'');
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
function bstrip(i){const bk=Object.entries(i.buckets||{}).filter(([k,v])=>v!=null&&!/Relative/.test(k));if(!bk.length)return '<span class="bstrip" aria-hidden="true"></span>';return `<span class="bstrip" title="${bk.map(([k,v])=>(k==='Filter'?'Macro filter':k)+' '+v).join(' · ')}" aria-label="Drivers: ${bk.map(([k,v])=>(k==='Filter'?'macro filter':k)+' '+v).join(', ')}">${bk.map(([k,v])=>`<i style="background:${bcol(v)}"></i>`).join('')}</span>`}
function convBar(i){return `<span class="cbar" title="Signal strength ${i.conv}/100 (${convWord(i.conv)})"><i style="width:${i.conv}%;background:${i.side==='buy'?'var(--b2)':'var(--b6)'}"></i></span>`}
function mom(i){if(i.d1==null)return '';const toward=i.d1<0?'buy':'sell';return `<span class="mom" title="1-month change ${i.d1>0?'+':''}${i.d1}, 3-month ${i.d3>0?'+':''}${i.d3}">${i.d1<0?'▼':'▲'} ${Math.abs(i.d1)}</span>`}
document.getElementById('nsig').textContent=`${items.length} readings from 11 models`;
document.getElementById('scale').innerHTML=BANDS.map(b=>`<div title="${b[0]}: ${b[1]===0?'1–20':b[2]===100?'81–100':(b[1]+1)+'–'+b[2]}"><span style="background:var(${b[3]})"></span><b class="lbl">${b[0]}</b><em class="rng">${b[1]===0?'1–20':b[2]===100?'81–100':(b[1]+1)+'–'+b[2]}</em></div>`).join('');

/* tooltip */
const tt=document.getElementById('tt');
function showTT(e,html){tt.innerHTML=html;tt.style.display='block';const x=Math.min(e.clientX+14,innerWidth-300),y=Math.min(e.clientY+14,innerHeight-tt.offsetHeight-10);tt.style.left=x+'px';tt.style.top=y+'px'}
function hideTT(){tt.style.display='none'}
function chip(s){const b=bandOf(s);return `<span class="chip"><span class="sw" style="background:var(${b[3]})"></span>${b[0]}</span>`}
function tierTag(t){const n={A:3,B:2,C:1}[t];return `<span class="conf" title="Confidence ${TIERS[t]}" aria-label="Confidence ${TIERNAME[t]}">${[0,1,2].map(k=>`<i class="${k<n?'':'o'}"></i>`).join('')}</span>`}

/* rows */
function rowHTML(i,extra){return `<div class="row" data-id="${i.id}" tabindex="0" role="button" aria-label="${esc(i.name)}, score ${i.score}, ${bandOf(i.score)[0]}"><span class="score">${i.score.toFixed(1)}</span><span class="sw" style="background:${bcol(i.score)}"></span><span class="nm">${esc(i.name)}</span>${HELD.has(i.id)?'<span class="held">You hold</span>':''}${extra||''}${mom(i)}${bstrip(i)}${tierTag(i.tier)}</div>`}
function bindRows(root){root.querySelectorAll('[data-id]').forEach(el=>{el.onclick=()=>openDrawer(el.dataset.id);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openDrawer(el.dataset.id)}}})}

/* holdings: one viewer's convenience, kept in this browser only */
let HELD=new Set();try{HELD=new Set(JSON.parse(localStorage.getItem('eeb-held')||'[]'))}catch(e){}
function saveHeld(){try{localStorage.setItem('eeb-held',JSON.stringify([...HELD]))}catch(e){}}
function toggleHeld(id){HELD.has(id)?HELD.delete(id):HELD.add(id);saveHeld();openDrawer(id);route(true)}
/* history helpers */
function prevScore(i){return i.history&&i.history.length>1?i.history[i.history.length-2][1]:null}

/* ---------- THIS MONTH ---------- */
function viewMonth(){
  const counts=BANDS.map(b=>HL().filter(i=>bandOf(i.score)===b).length);
  const buyZone=HL().filter(i=>i.score<=35&&!notInvestable(i));
  const trimZone=HL().filter(i=>i.score>65);
  const withHist=items.filter(i=>i.history&&i.history.length>1);
  const moved=withHist.filter(i=>bandOf(prevScore(i))!==bandOf(i.score));
  const groupList=(list,dir)=>{
    const groups=MODEL_ORDER.map(m=>[m,list.filter(i=>i.model===m).sort((a,b)=>dir*(a.score-b.score))]).filter(g=>g[1].length);
    groups.sort((x,y)=>dir*(x[1][0].score-y[1][0].score));
    return groups.map(([m,l])=>`<div class="grp">${MODELS[m]}</div>`+l.slice(0,3).map(i=>rowHTML(i,`<span class="tag" title="${esc(shortAct(i))}">${esc(shortAct(i))}</span>`)).join('')+(l.length>3?`<a class="more" href="#map" onclick="mapState.model='${m}'">See all ${l.length} on the map</a>`:'')).join('');};
  const heldTrim=trimZone.filter(i=>HELD.has(i.id)).sort((a,b)=>b.score-a.score);
  const heldAll=items.filter(i=>HELD.has(i.id));
  const ac=Object.fromEntries(DATA.assetClasses.map(a=>[a.id,a]));
  const reits=items.filter(i=>i.model==='reits').map(i=>i.score).sort((a,b)=>a-b);
  const reitMed=reits[Math.floor(reits.length/2)];
  const dis=[
    {t:'Listed REITs',a:`Asset-class model: ${ac.REIT.score} (yield vs G-sec only)`,b:`Trust-level median: ${reitMed} (adds price-to-NAV discounts)`,gap:Math.abs(ac.REIT.score-reitMed),ids:['RE_BIRET']},
    {t:'US equities',a:`Asset-class valuation: ${ac.US_EQ.score}`,b:`Own-model oscillator: ${ac.US_EQ.own} (adds timing and macro)`,gap:Math.abs(ac.US_EQ.score-ac.US_EQ.own),ids:['GLB_SP500']},
    {t:'Gold',a:`Asset-class valuation: ${ac.GOLD.score}`,b:`Gold oscillator: ${byId.GOLD.score} (macro supportive at 35.5)`,gap:Math.abs(ac.GOLD.score-byId.GOLD.score),ids:['GOLD']},
    {t:'Nifty 50',a:`Nifty oscillator: ${byId.NIFTY50.score}`,b:`Global 5-yr lens: ${byId.GLB_NIFTY50.score}`,gap:Math.abs(byId.NIFTY50.score-byId.GLB_NIFTY50.score),ids:['NIFTY50']},
  ].sort((x,y)=>y.gap-x.gap);
  const tot=HL().length;
  const into=(b)=>moved.filter(i=>bandOf(i.score)[0]===b).map(i=>i.name);
  const join=l=>l.length<2?l.join(''):l.slice(0,-1).join(', ')+' and '+l[l.length-1];
  const intoBuy=into('Buy'),intoHold=moved.filter(i=>bandOf(i.score)[0]==='Hold');
  const bestBond=items.filter(i=>i.model==='bonds').sort((a,b)=>a.score-b.score)[0];
  const lede=`${moved.length} of the ${withHist.length} long-history models changed band this month. <b>${join(intoBuy)}</b> moved into Buy; ${join(intoHold.map(i=>i.name+' '+(prevScore(i)>i.score?'eased':'rose')+' from '+bandOf(prevScore(i))[0]))} to Hold. ${(()=>{const top=sd=>items.filter(i=>!notInvestable(i)&&i.side===sd).sort((a,b)=>b.conv-a.conv)[0];const b=top('buy'),s=top('sell');return `Strongest buy signal: <b>${esc(b.name)}</b> (strength ${b.conv}); strongest sell: <b>${esc(s.name)}</b> (${s.conv}). `})()}For new money, <b>${esc(bestBond.name.split(' (')[0].toLowerCase())}</b> (${bestBond.score}) is the cleanest Buy; Pharma and most of Europe sit in Trim.`;
  return `
  <section class="card brief" aria-labelledby="bh">
    <div class="tag" id="bh">${MONTHNAME} brief</div>
    <p class="lede">${lede}</p>
    <div class="moves">${moved.map(i=>`<span class="move" data-id="${i.id}" role="button" tabindex="0"><span class="sw" style="background:${bcol(i.score)}"></span>${esc(i.name)}: ${bandOf(prevScore(i))[0]} → <b>${bandOf(i.score)[0]}</b></span>`).join('')}</div>
  </section>
  <div class="grid g2" style="margin-bottom:14px">
    <section class="card"><h2>Add to: score 35 or lower</h2><p class="hint">${buyZone.length} investable readings. Best three per model, best model first, with the model's own instruction.</p>${groupList(buyZone,1)}</section>
    <section class="card"><h2>Trim if you hold it: score above 65</h2><p class="hint">${trimZone.length} readings. These only matter for positions you own.</p>
      ${heldAll.length?(heldTrim.length?`<div class="grp">Your positions in Trim or Exit</div>${heldTrim.map(i=>rowHTML(i,'')).join('')}`:`<div class="empty">None of your ${heldAll.length} marked position${heldAll.length>1?'s are':' is'} in Trim or Exit.</div>`):`<div class="empty">Mark what you own (open any reading and press <b>I hold this</b>) and your positions will be listed first here.</div>`}
      ${groupList(trimZone,-1)}</section>
  </div>
  <section class="card" style="margin-bottom:14px">
    <h2>Band changes since last month</h2>
    <p class="hint">Only five models have monthly history. The rest start their trend after the next monthly run.</p>
    <div class="chg">${withHist.sort((a,b)=>(bandOf(prevScore(b))!==bandOf(b.score))-(bandOf(prevScore(a))!==bandOf(a.score))).map(i=>{const p=prevScore(i),pb=bandOf(p)[0],nb=bandOf(i.score)[0],d=(i.score-p).toFixed(1);return `<div class="chgc" data-id="${i.id}" role="button" tabindex="0"><div class="n">${esc(i.name)}</div><div style="margin:4px 0">${spark(i.history.slice(-12),150,40)}</div><div class="t">${p} → <b style="color:var(--ink)">${i.score}</b> (${d>0?'+':''}${d})</div><div class="t" style="margin-top:4px">${pb===nb?`Still ${nb}`:`<span class="moved">${pb} → ${nb}</span>`}</div></div>`}).join('')}</div>
  </section>
  <div class="grid g2">
  <section class="card">
    <h2>Market temperature</h2>
    <p class="hint">All ${tot} headline readings by band (Nifty 500 stocks outside the Nifty 50 are on the map). Mostly mid-range: the useful readings are at the edges.</p>
    <div class="dist" role="img" aria-label="${counts.map((c,k)=>BANDS[k][0]+' '+c).join(', ')}">${counts.map((c,k)=>c?`<div style="flex:${c};background:var(${BANDS[k][3]})"></div>`:'').join('')}</div>
    <div class="legend">${counts.map((c,k)=>`<span><span class="sw" style="background:var(${BANDS[k][3]})"></span> ${BANDS[k][0]} <b>${c}</b></span>`).join('')}</div>
    <div class="note">${Math.round(100*HL().filter(i=>i.tier!=='A').length/tot)}% of readings have only one month of history, so treat single-month calls as indicative.</div>
  </section>
  <section class="card">
    <h2>Where models disagree</h2>
    <p class="hint">A gap of 10+ points between two views of one asset is worth a look before acting.</p>
    <table><thead><tr><th scope="col">Asset</th><th scope="col">Views</th><th scope="col" style="text-align:right">Gap</th></tr></thead><tbody>
    ${dis.map(d=>`<tr class="row" data-id="${d.ids[0]}" tabindex="0" style="display:table-row"><td><b>${d.t}</b></td><td>${esc(d.a)}<br>${esc(d.b)}</td><td style="text-align:right"><b>${d.gap.toFixed(1)}</b>${d.gap>=10?'<br><span class="pill" style="border-color:#fab219">check</span>':''}</td></tr>`).join('')}
    </tbody></table>
  </section></div>
  ${healthHTML()}`;
}
function shortAct(i){
  if(i.model==='global')return i.action||'';
  if(['bonds','carry'].includes(i.model))return i.action||'';
  if(i.model==='crypto')return 'Buy, staged';
  if(i.model==='sectors'||i.model==='factors')return i.action==='Neutral'?'':i.action;
  if(i.model==='stocks')return i.meta.Sector||'';
  if(i.model==='property')return 'valuation only';
  return '';
}

/* sparkline */
function spark(h,w,ht){
  if(!h||h.length<2)return '';
  const xs=k=>k*(w-4)/(h.length-1)+2, ys=v=>ht-2-(v/100)*(ht-4);
  const d=h.map((p,k)=>(k?'L':'M')+xs(k).toFixed(1)+','+ys(p[1]).toFixed(1)).join('');
  const last=h[h.length-1][1];
  return `<svg width="${w}" height="${ht}" viewBox="0 0 ${w} ${ht}" style="max-width:100%;height:auto" aria-hidden="true"><rect x="0" y="${ys(35)}" width="${w}" height="${ys(0)-ys(35)}" fill="var(--b3)" opacity=".35"/><rect x="0" y="${ys(100)}" width="${w}" height="${ys(65)-ys(100)}" fill="var(--b5)" opacity=".3"/><path d="${d}" fill="none" stroke="var(--ink)" stroke-width="1.5"/><circle cx="${xs(h.length-1)}" cy="${ys(last)}" r="3" fill="${bcol(last)}" stroke="var(--ink)" stroke-width="1"/></svg>`;
}

/* ---------- SIGNAL FINDER ---------- */
let sigState={model:'all'};
function laneCard(i){return `<div class="lc" data-id="${i.id}" role="button" tabindex="0" aria-label="${esc(i.name)}, score ${i.score}, signal strength ${i.conv}"><div class="top"><span>${HELD.has(i.id)?'<span class="held">You hold</span> ':''}${esc(i.name)}</span><b>${i.score.toFixed(1)}</b></div><div class="bot">${convBar(i)}<span>${i.conv}</span>${bstrip(i)}${mom(i)}<span style="margin-left:auto">${tierTag(i.tier)}</span></div></div>`}
function viewSignals(){
  const lanes=['buy','stage','near','rally','trimnow'].map(k=>[k,HL().filter(i=>i.lane===k).sort((a,b)=>b.conv-a.conv)]);
  const top=(side)=>HL().filter(i=>i.side===side&&!notInvestable(i)).sort((a,b)=>b.conv-a.conv).slice(0,10);
  const rankRows=(l)=>l.map((i,k)=>`<div class="rank" data-id="${i.id}" role="button" tabindex="0"><span class="tag">${k+1}</span><span class="n">${esc(i.name)} <span class="tag">${MODELS[i.model]}</span></span>${bstrip(i)}<span>${tierTag(i.tier)}</span>${convBar(i)}<span class="cv">${i.conv}</span></div>`).join('');
  return `
  <section class="card" style="margin-bottom:14px">
    <h2>Action lanes: what each reading is telling you to do</h2>
    <p class="hint">Every reading in or near a trading zone, sorted by signal strength. The lane uses the score plus its timing and macro buckets, so a cheap asset with timing against it lands in "Buy in stages", not "Buy now".</p>
    <div class="lanes">${lanes.map(([k,l])=>`<div class="lane"><h3>${LANES[k][0]}<span class="tag">${l.length}</span></h3><p class="hint">${LANES[k][1]}</p>${l.slice(0,7).map(laneCard).join('')}${l.length>7?`<div class="more">+${l.length-7} more, weaker</div>`:''}${!l.length?'<div class="empty">Nothing here this month.</div>':''}</div>`).join('')}</div>
    <div class="legend" style="margin-top:10px"><span>${convBar({conv:70,side:'buy'})} Signal strength 0–100</span><span><span class="bstrip"><i style="background:var(--b2)"></i><i style="background:var(--b4)"></i><i style="background:var(--b5)"></i></span> Drivers, one square per bucket (valuation, timing, macro…), coloured by band</span><span>▼ 1-month move toward Buy, ▲ toward Sell (history models only)</span></div>
  </section>
  <div class="grid g2" style="margin-bottom:14px">
    <section class="card"><h2>Strongest buy signals</h2><p class="hint">Ranked by strength = how far from 50 × how many drivers agree × confidence.</p>${rankRows(top('buy'))}</section>
    <section class="card"><h2>Strongest sell signals</h2><p class="hint">Same measure, rich side. Only matters for what you hold.</p>${rankRows(top('sell'))}</section>
  </div>
  <section class="card" style="margin-bottom:14px">
    <h2>Value vs timing</h2>
    <p class="hint">Valuation bucket across, timing bucket up (stocks use momentum). Bottom-left is the cleanest entry: cheap and timing supportive. Top-right is the cleanest exit. Dot size is signal strength; colour is the overall band.</p>
    <div class="filters"><label class="sr" for="ssel">Model</label><select id="ssel" class="btn">${['all',...MODEL_ORDER.filter(m=>items.some(i=>i.model===m&&i.V!=null&&i.T!=null))].map(m=>`<option value="${m}" ${sigState.model===m?'selected':''}>${m==='all'?'All models with both buckets':MODELS[m]}</option>`).join('')}</select></div>
    <div id="vtsvg"></div>
  </section>
  ${items.some(i=>i.model==='stocks')?`<section class="card">
    <h2>Sector vs its stocks</h2>
    <p class="hint">Does the sector call hold up stock by stock? Filled dot is the sector index score; small dots are the Nifty stocks in it (sectors with two or more); the diamond is their median. A wide gap or a wide spread means the sector call depends on which stocks you buy.</p>
    <div id="sxsvg"></div>
  </section>`:''}`;
}
function drawSignals(){
  bindRows(document.getElementById('view'));
  const sel=document.getElementById('ssel');sel.onchange=()=>{sigState.model=sel.value;drawVT()};
  drawVT();if(document.getElementById('sxsvg'))drawSX();
}
function drawVT(){
  const el=document.getElementById('vtsvg');if(!el)return;
  const W=el.clientWidth,H=Math.min(460,W*.55),L=40,R=16,T=12,B=34;
  const x=v=>L+(v-1)/99*(W-L-R),y=v=>T+(100-v)/99*(H-T-B);
  const pts=(sigState.model==='all'?HL():items).filter(i=>i.V!=null&&i.T!=null&&(sigState.model==='all'||i.model===sigState.model)&&!notInvestable(i));
  let s=`<svg width="${W}" height="${H}" role="group" aria-label="Valuation versus timing scatter">`;
  const q=[[1,50,1,50,'var(--b2)','Cheap · timing supportive → buy now'],[1,50,50,100,'var(--b3)','Cheap · timing against → stage entries'],[50,100,50,100,'var(--b6)','Rich · timing against → trim now'],[50,100,1,50,'var(--b5)','Rich · timing still OK → trim into rallies']];
  q.forEach(([x0,x1,y0,y1,c,l])=>{s+=`<rect x="${x(x0)}" y="${y(y1)}" width="${x(x1)-x(x0)}" height="${y(y0)-y(y1)}" fill="${c}" opacity=".07"/>`;s+=`<text x="${x0<50?x(x0)+8:x(x1)-8}" y="${y0<50?y(y0)-8:y(y1)+16}" text-anchor="${x0<50?'start':'end'}" style="font-weight:600;fill:var(--ink-2)">${l}</text>`});
  [20,35,50,65,80].forEach(v=>{s+=`<line x1="${x(v)}" x2="${x(v)}" y1="${T}" y2="${H-B}" stroke="var(--line)" ${v===50?'stroke="var(--line-2)" stroke-width="1.5"':''}/><line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${x(v)}" y="${H-B+14}" text-anchor="middle">${v}</text><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${v}</text>`});
  s+=`<line x1="${x(50)}" x2="${x(50)}" y1="${T}" y2="${H-B}" stroke="var(--ink-3)"/><line x1="${L}" x2="${W-R}" y1="${y(50)}" y2="${y(50)}" stroke="var(--ink-3)"/>`;
  s+=`<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">Valuation bucket: cheap ← → rich</text><text transform="translate(12,${(T+H-B)/2}) rotate(-90)" text-anchor="middle">Timing: supportive ↓ ↑ against</text>`;
  pts.sort((a,b)=>a.conv-b.conv).forEach(i=>{const r=3.5+i.conv/14,c=bcol(i.score);
    const st=i.tier==='C'?`fill="var(--surface)" stroke="${c}" stroke-width="2"`:`fill="${c}" stroke="${i.tier==='A'?'var(--ink)':'var(--surface)'}" stroke-width="1.5"`;
    s+=`<g class="dot" data-id="${i.id}" tabindex="0" role="button" aria-label="${esc(i.name)}: valuation ${i.V}, timing ${i.T}, score ${i.score}" style="cursor:pointer"><circle cx="${x(i.V)}" cy="${y(i.T)}" r="${Math.max(r,9)}" fill="transparent"/><circle cx="${x(i.V)}" cy="${y(i.T)}" r="${r}" ${st} opacity=".9"/>${i.conv>=45||i.tier==='A'||HELD.has(i.id)?(()=>{const lx=x(i.V),flip=lx>W-160;return `<text x="${flip?lx-r-3:lx+r+3}" y="${y(i.T)+4}" text-anchor="${flip?'end':'start'}" style="fill:var(--ink);font-size:12px">${esc(i.name.replace(' (global 5-yr lens)',''))}</text>`})():''}</g>`});
  s+='</svg>';el.innerHTML=s;bindDots(el);
}
function bindDots(el){el.querySelectorAll('.dot').forEach(g=>{const i=byId[g.dataset.id];
  const tip=`<b>${esc(i.name)}</b><br>Score ${i.score} · ${bandOf(i.score)[0]}<br>Valuation ${i.V??'–'} · Timing ${i.T??'–'}${i.F!=null?' · Macro '+i.F:''}<br>Signal strength ${i.conv} (${convWord(i.conv)}) · confidence ${TIERNAME[i.tier]}`;
  g.onmousemove=e=>showTT(e,tip);g.onmouseleave=hideTT;g.onclick=()=>{hideTT();openDrawer(i.id)};
  g.onfocus=()=>{const r=g.getBoundingClientRect();showTT({clientX:r.right,clientY:r.top},tip)};g.onblur=hideTT;
  g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hideTT();openDrawer(i.id)}}})}
function drawSX(){
  const el=document.getElementById('sxsvg');if(!el)return;
  const stocks=items.filter(i=>i.model==='stocks'&&i.sidx&&byId['SEC_'+i.sidx]);
  const rows=[...new Set(stocks.map(i=>i.sidx))].filter(k=>stocks.filter(i=>i.sidx===k).length>=2).map(k=>{const st=stocks.filter(i=>i.sidx===k).sort((a,b)=>a.score-b.score);const med=st.length%2?st[(st.length-1)/2].score:(st[st.length/2-1].score+st[st.length/2].score)/2;return {sec:byId['SEC_'+k],st,med:+med.toFixed(1)}}).sort((a,b)=>Math.abs(b.sec.score-b.med)-Math.abs(a.sec.score-a.med));
  const W=el.clientWidth,L=190,R=150,rh=34,T=22;const x=v=>L+(v-1)/99*(W-L-R);
  let s=`<svg width="${W}" height="${T+rows.length*rh+20}" role="group" aria-label="Sector scores against their stocks">`;
  BANDS.forEach((b,k)=>s+=`<rect x="${x(Math.max(1,b[1]))}" y="${T-4}" width="${x(b[2])-x(Math.max(1,b[1]))}" height="${rows.length*rh}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/><text x="${(x(Math.max(1,b[1]))+x(b[2]))/2}" y="12" text-anchor="middle">${b[0]}</text>`);
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

/* ---------- OPPORTUNITY MAP ---------- */
let mapState={q:'',tier:'all',hideNI:true,model:'all',held:false,mode:'chart',sort:'score'};
function viewMap(){
  return `<div class="card">
  <h2>Opportunity map: every reading on one 1–100 scale</h2>
  <p class="hint">One dot per instrument, one row per model. Left is cheap, right is rich. Hover or focus a dot for its reading; click or press Enter for the drivers.</p>
  <div class="filters" role="group" aria-label="Filters">
    <label class="sr" for="q">Search</label><input id="q" type="search" placeholder="Search: IT, Infosys, Japan, REIT…" value="${esc(mapState.q)}">
    <label class="sr" for="msel">Model</label><select id="msel" class="btn">${['all',...MODEL_ORDER.filter(m=>items.some(i=>i.model===m))].map(m=>`<option value="${m}" ${mapState.model===m?'selected':''}>${m==='all'?'All models':MODELS[m]}</option>`).join('')}</select>
    <span class="seg" id="tierseg" aria-label="Confidence"><button data-v="all">Any confidence</button><button data-v="AB">Medium and high</button><button data-v="A">High only</button></span>
    <button class="btn ${mapState.held?'on':''}" id="heldb" aria-pressed="${mapState.held}">My holdings${HELD.size?' ('+HELD.size+')':''}</button>
    <label class="toggle" id="ni"><input type="checkbox" ${mapState.hideNI?'checked':''}> Hide not investable from India</label>
    <span class="seg" id="modeseg" style="margin-left:auto" aria-label="View as"><button data-v="chart">Chart</button><button data-v="table">Table</button></span>
  </div>
  <div class="legend" id="maplegend"><span>Confidence:</span><span><svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill="var(--b2)" stroke="var(--ink)" stroke-width="1.6"/></svg> High (history)</span><span><svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="var(--b2)"/></svg> Medium</span><span><svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="4.5" fill="var(--surface)" stroke="var(--b2)" stroke-width="2"/></svg> Low (thin inputs)</span><span><svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="2 2"/></svg> You hold</span></div>
  <div id="mapsvg"></div></div>`;
}
function hash(s){let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))|0;return Math.abs(h)}
function mapFilter(){
  const q=mapState.q.toLowerCase();
  return {vis:i=>(mapState.tier==='all'||mapState.tier.includes(i.tier))&&!(mapState.hideNI&&notInvestable(i))&&(!mapState.held||HELD.has(i.id))&&(mapState.model==='all'||i.model===mapState.model),
          match:i=>!q||(i.name+' '+(i.meta?.Ticker||'')+' '+(i.meta?.Sector||'')+' '+(i.meta?.Economy||'')+' '+(i.meta?.Type||'')).toLowerCase().includes(q)};
}
function drawMap(){
  const el=document.getElementById('mapsvg');if(!el)return;
  const {vis,match}=mapFilter();
  document.getElementById('maplegend').style.display=mapState.mode==='chart'?'':'none';
  if(mapState.mode==='table'){
    const rows=items.filter(i=>vis(i)&&match(i));
    const key={score:(a,b)=>a.score-b.score,name:(a,b)=>a.name.localeCompare(b.name),model:(a,b)=>MODEL_ORDER.indexOf(a.model)-MODEL_ORDER.indexOf(b.model)||a.score-b.score}[mapState.sort];
    rows.sort(key);
    el.innerHTML=`<table><caption class="sr">All readings, sorted by ${mapState.sort}</caption><thead><tr><th scope="col"><button class="btn" data-s="name">Name</button></th><th scope="col"><button class="btn" data-s="model">Model</button></th><th scope="col" style="text-align:right"><button class="btn" data-s="score">Score</button></th><th scope="col">Band</th><th scope="col">Confidence</th><th scope="col">Model's instruction</th></tr></thead><tbody>${rows.map(i=>`<tr class="row" style="display:table-row" data-id="${i.id}" tabindex="0"><td><b>${esc(i.name)}</b> ${HELD.has(i.id)?'<span class="held">You hold</span>':''}</td><td>${MODELS[i.model]}</td><td style="text-align:right"><b>${i.score.toFixed(1)}</b></td><td class="nw">${chip(i.score)}</td><td class="nw">${tierTag(i.tier)} ${TIERNAME[i.tier]}</td><td style="color:var(--ink-2)">${esc(i.action||'')}</td></tr>`).join('')||'<tr><td colspan="6">No readings match. Clear the search or widen the filters.</td></tr>'}</tbody></table>`;
    el.querySelectorAll('[data-s]').forEach(b=>b.onclick=()=>{mapState.sort=b.dataset.s;drawMap()});bindRows(el);return;
  }
  const W=el.clientWidth,L=170,R=16,top=26;
  const models=MODEL_ORDER.filter(m=>(mapState.model==='all'||m===mapState.model)&&items.some(i=>i.model===m));
  const rh=m=>m==='stocks'?(items.filter(i=>i.model==='stocks').length>100?180:92):m==='global'?70:52;
  const H=models.reduce((s,m)=>s+rh(m),0);
  const x=v=>L+(v-1)/99*(W-L-R);
  let s=`<svg width="${W}" height="${top+H+24}" role="group" aria-label="Strip plot of readings by model">`;
  BANDS.forEach((b,k)=>{s+=`<rect x="${x(Math.max(1,b[1]))}" y="${top-6}" width="${x(b[2])-x(Math.max(1,b[1]))}" height="${H+6}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/><text x="${(x(Math.max(1,b[1]))+x(b[2]))/2}" y="12" text-anchor="middle">${b[0]}</text>`});
  [20,35,50,65,80].forEach(v=>s+=`<line x1="${x(v)}" x2="${x(v)}" y1="${top-6}" y2="${top+H}" stroke="var(--line-2)" stroke-width="1"/>`);
  [1,20,35,50,65,80,100].forEach(v=>s+=`<text x="${x(v)}" y="${top+H+16}" text-anchor="middle">${v}</text>`);
  let y0=top;
  models.forEach(m=>{
    const h=rh(m),cy=y0+h/2;
    const all=items.filter(i=>i.model===m),n=all.length;
    s+=`<line x1="${L}" x2="${W-R}" y1="${y0+h}" y2="${y0+h}" stroke="var(--line)"/>`;
    s+=`<text x="0" y="${cy-2}" style="fill:var(--ink);font-weight:500;font-size:12px">${MODELS[m]}</text><text x="0" y="${cy+13}">${n} reading${n>1?'s':''}</text>`;
    let lab=0;
    all.forEach(i=>{
      if(!vis(i))return;
      const mt=match(i);
      const jy=n>3?((hash(i.id)%100)/100-.5)*(h-22):0;
      const cx=x(i.score),c=bcol(i.score),cyy=cy+jy;
      const style=i.tier==='C'?`fill="var(--surface)" stroke="${c}" stroke-width="2.2"`:i.tier==='A'?`fill="${c}" stroke="var(--ink)" stroke-width="1.6"`:`fill="${c}" stroke="var(--surface)" stroke-width="1.5"`;
      const showLab=i.tier==='A'||HELD.has(i.id)||(mapState.q&&mt);
      s+=`<g class="dot" data-id="${i.id}" tabindex="${mt?0:-1}" role="button" aria-label="${esc(i.name)}, ${i.score}, ${bandOf(i.score)[0]}, confidence ${TIERNAME[i.tier]}" style="cursor:pointer;opacity:${mt?1:.12}"><circle cx="${cx}" cy="${cyy}" r="12" fill="transparent"/>${HELD.has(i.id)?`<circle cx="${cx}" cy="${cyy}" r="10" fill="none" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="2 2"/>`:''}<circle cx="${cx}" cy="${cyy}" r="${i.tier==='A'?7:5.5}" ${style}/>${showLab?`<text x="${cx+((lab++)%2?9:-9)}" y="${cyy-10}" text-anchor="${lab%2?'end':'start'}" style="fill:var(--ink);font-size:12px;font-weight:500">${esc(i.name.replace(' (global 5-yr lens)',''))}</text>`:''}</g>`;
    });
    y0+=h;
  });
  s+='</svg>';el.innerHTML=s;
  el.querySelectorAll('.dot').forEach(g=>{const i=byId[g.dataset.id];
    const tip=`<b>${esc(i.name)}</b><br>${i.score} · ${bandOf(i.score)[0]} · confidence ${TIERNAME[i.tier]}<br><span style="opacity:.8">${esc(MODELS[i.model])}${i.action?'<br>'+esc(i.action):''}</span>`;
    g.onmousemove=e=>showTT(e,tip);g.onmouseleave=hideTT;g.onclick=()=>{hideTT();openDrawer(i.id)};
    g.onfocus=()=>{const r=g.getBoundingClientRect();showTT({clientX:r.right,clientY:r.top},tip)};g.onblur=hideTT;
    g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();hideTT();openDrawer(i.id)}}});
}
function bindMap(){
  const q=document.getElementById('q');q.oninput=()=>{mapState.q=q.value;drawMap()};
  document.getElementById('msel').onchange=e=>{mapState.model=e.target.value;drawMap()};
  document.querySelectorAll('#tierseg button').forEach(b=>{b.classList.toggle('on',b.dataset.v===mapState.tier);b.setAttribute('aria-pressed',b.dataset.v===mapState.tier);b.onclick=()=>{mapState.tier=b.dataset.v;bindMap()}});
  document.querySelectorAll('#modeseg button').forEach(b=>{b.classList.toggle('on',b.dataset.v===mapState.mode);b.setAttribute('aria-pressed',b.dataset.v===mapState.mode);b.onclick=()=>{mapState.mode=b.dataset.v;bindMap()}});
  document.getElementById('heldb').onclick=e=>{mapState.held=!mapState.held;e.currentTarget.classList.toggle('on',mapState.held);e.currentTarget.setAttribute('aria-pressed',mapState.held);drawMap()};
  document.querySelector('#ni input').onchange=e=>{mapState.hideNI=e.target.checked;drawMap()};
  drawMap();
}

/* ---------- ASSET CLASSES ---------- */
function viewClasses(){
  return `<div class="card"><h2>Asset classes: top of the hierarchy</h2>
  <p class="hint">The asset-class model ranks 15 assets on valuation alone (filled dot). Where a dedicated model exists, its full oscillator (valuation + timing + filter) is the ring; the line is the gap. Bitcoin added from its own model. Click a row to drill into that model's instruments.</p>
  <div class="legend"><span><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="var(--ink-2)"/></svg> Valuation (asset-class model)</span><span><svg width="14" height="14"><circle cx="7" cy="7" r="4.5" fill="var(--surface)" stroke="var(--ink)" stroke-width="2"/></svg> Dedicated model oscillator</span></div>
  <div id="acsvg"></div></div>`;
}
const AC_MODEL={SHORT_DEBT:['bonds','FI_SHORT_1Y'],US_TREASURY:[null],GSEC_LONG:['bonds','FI_GSEC_10Y'],SILVER:['commodities','CMD_SILVER'],CREDIT_AA:['bonds','FI_CREDIT_AA_3Y'],CORP_AAA:['bonds','FI_CORP_AAA_5Y'],RESI_RE:['property'],CASH:[null],MIDCAP:['sectors','SEC_MIDCAP150'],NIFTY50:['core','NIFTY50'],GOLD:['core','GOLD'],GLOBAL_EQ:['global','GLB_ACWI'],SMALLCAP:['sectors','SEC_SMALLCAP250'],US_EQ:['global','GLB_SP500'],REIT:['reits']};
function drawClasses(){
  const el=document.getElementById('acsvg');if(!el||el.clientWidth<80)return;
  const rows=[...DATA.assetClasses.map(a=>{const m=AC_MODEL[a.id]||[null];const own=m[1]&&byId[m[1]]?byId[m[1]].score:null;return {...a,own2:own,model:m[0],target:m[1]}}),{id:'BTC',name:'Bitcoin (own model; not in asset-class model)',score:null,own2:byId.BTC.score,tilt:'Buy, staged; cap 5% of portfolio',model:'crypto',target:'BTC'}];
  const W=el.clientWidth,L=Math.min(330,W*.38),R=190,rh=30,top=24;const x=v=>L+(v-1)/99*(W-L-R);
  let s=`<svg width="${W}" height="${top+rh*rows.length+6}">`;
  BANDS.forEach((b,k)=>s+=`<rect x="${x(Math.max(1,b[1]))}" y="${top-4}" width="${x(b[2])-x(Math.max(1,b[1]))}" height="${rh*rows.length}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/><text x="${(x(Math.max(1,b[1]))+x(b[2]))/2}" y="12" text-anchor="middle">${b[0]}</text>`);
  s+=`<text x="${W-R+12}" y="12">Model tilt</text>`;
  rows.forEach((a,k)=>{const cy=top+k*rh+rh/2;
    s+=`<g class="acr" data-k="${k}" style="cursor:pointer"><rect x="0" y="${cy-rh/2}" width="${W}" height="${rh}" fill="transparent"/><line x1="0" x2="${W}" y1="${cy+rh/2}" y2="${cy+rh/2}" stroke="var(--line)"/><text x="0" y="${cy+4}" style="fill:var(--ink);font-size:12px">${esc(a.name.length>44?a.name.slice(0,42)+'…':a.name)}</text>`;
    if(a.score!=null&&a.own2!=null)s+=`<line x1="${x(a.score)}" x2="${x(a.own2)}" y1="${cy}" y2="${cy}" stroke="var(--ink-3)" stroke-width="2"/>`;
    if(a.score!=null)s+=`<circle cx="${x(a.score)}" cy="${cy}" r="6" fill="${bcol(a.score)}" stroke="var(--ink-2)" stroke-width="1.2"/>`;
    if(a.own2!=null)s+=`<circle cx="${x(a.own2)}" cy="${cy}" r="5.5" fill="var(--surface)" stroke="var(--ink)" stroke-width="2"/>`;
    {const vals=[a.score,a.own2].filter(v=>v!=null);const lo=Math.min(...vals),hi=Math.max(...vals);
     if(a.score!=null)s+=`<text x="${a.score<=hi&&a.own2!=null&&a.score<a.own2?x(a.score)-10:x(a.score)+10}" y="${cy+4}" text-anchor="${a.own2!=null&&a.score<a.own2?'end':'start'}" style="fill:var(--ink);font-weight:600">${a.score}</text>`;
     if(a.own2!=null)s+=`<text x="${a.score!=null&&a.score<a.own2?x(a.own2)+10:x(a.own2)-10}" y="${cy+4}" text-anchor="${a.score!=null&&a.score<a.own2?'start':'end'}">${a.own2}</text>`;}
    s+=`<text x="${W-R+12}" y="${cy+4}">${esc(a.tilt||'')}</text></g>`});
  s+='</svg>';el.innerHTML=s;
  el.querySelectorAll('.acr').forEach(g=>{const a=rows[+g.dataset.k];
    g.onmousemove=e=>showTT(e,`<b>${esc(a.name)}</b><br>${a.score!=null?'Valuation '+a.score+' ('+esc(a.read)+')<br>':''}${a.own2!=null?'Dedicated model '+a.own2+'<br>':''}${a.yield_!=null?'Income yield '+a.yield_+'%<br>':''}<span style="opacity:.8">${esc(a.drivers||'')}</span>`);
    g.onmouseleave=hideTT;
    g.onclick=()=>{hideTT();if(a.target)openDrawer(a.target);else if(a.model){mapState.q='';location.hash='map';}}});
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
  <div id="tsvg"></div></div>
  <div class="card"><h2>Band timeline</h2><p class="hint">One cell per month, coloured by band. Shows how long each asset sat in a zone, which is what matters for a 5-year holder: entries made in long blue stretches, trims in red ones.</p><div id="bsvg"></div></div>`;
}
function drawTrends(){
  const el=document.getElementById('tsvg');if(!el)return;
  const W=el.clientWidth,H=300,L=34,R=90,T=10,B=26;
  const months=byId.GOLD.history.map(h=>h[0]).slice(-trendState.range);
  const x=k=>L+k*(W-L-R)/(months.length-1),y=v=>T+(100-v)/100*(H-T-B);
  let s=`<svg width="${W}" height="${H}" role="img" aria-label="Oscillator history">`;
  BANDS.forEach((b,k)=>s+=`<rect x="${L}" y="${y(b[2])}" width="${W-L-R}" height="${y(b[1])-y(b[2])}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.06:.09}"/>`);
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
  // band timeline
  const be=document.getElementById('bsvg');const W2=be.clientWidth,L2=110,allM=byId.GOLD.history.map(h=>h[0]),cw=(W2-L2)/allM.length;
  let t=`<svg width="${W2}" height="${SERIES.length*26+22}">`;
  SERIES.forEach(([id],r)=>{const map=Object.fromEntries(byId[id].history);t+=`<text x="0" y="${r*26+17}" style="fill:var(--ink)">${esc(byId[id].name)}</text>`;
    allM.forEach((m,k)=>{const v=map[m];if(v==null)return;t+=`<rect class="bc" data-t="${esc(byId[id].name)} ${m}: ${v} · ${bandOf(v)[0]}" x="${L2+k*cw}" y="${r*26+4}" width="${Math.max(1,cw-1.5)}" height="20" rx="2" fill="var(${bandOf(v)[3]})"/>`})});
  allM.forEach((m,k)=>{if(m.endsWith('-01'))t+=`<text x="${L2+k*cw}" y="${SERIES.length*26+18}">${m.slice(0,4)}</text>`});
  t+='</svg>';be.innerHTML=t;be.querySelectorAll('.bc').forEach(r=>{r.onmousemove=e=>showTT(e,r.dataset.t);r.onmouseleave=hideTT});
}
function bindTrends(){
  document.querySelectorAll('#stog .toggle').forEach(t=>t.onclick=()=>{trendState.on[t.dataset.id]^=1;t.classList.toggle('off');drawTrends()});
  document.querySelectorAll('#rseg button').forEach(b=>{b.classList.toggle('on',+b.dataset.v===trendState.range);b.onclick=()=>{trendState.range=+b.dataset.v;bindTrends()}});
  drawTrends();
}

/* ---------- ALERTS ---------- */
function viewAlerts(){
  const withHist=items.filter(i=>i.history&&i.history.length>1);
  const fired=[];
  withHist.forEach(i=>{const p=prevScore(i),pb=bandOf(p)[0],nb=bandOf(i.score)[0];if(pb!==nb)fired.push(['Band change',i,`${pb} → ${nb} (${p} → ${i.score})`]);});
  withHist.forEach(i=>{const h=i.history.slice(-4).map(x=>x[1]);if(h.length===4&&h.every((v,k)=>!k||v<h[k-1]))fired.push(['3-month drift',i,`Falling three months in a row: ${h.join(' → ')}`]);});
  const b=byId.BTC;if(items.includes(b)&&b.buckets.Filter>65)fired.push(['Staging rule',b,`Score in Buy but macro filter ${b.buckets.Filter}: enter in tranches, not lump sum`]);
  items.filter(i=>i.score>80).forEach(i=>fired.push(['Exit zone',i,`Score ${i.score} (>80)`]));
  items.filter(i=>i.parabolic&&i.parabolic.status!=='Normal').sort((a,b)=>b.parabolic.gap-a.parabolic.gap).forEach(i=>fired.push([i.parabolic.status==='Parabolic'?'Parabolic move':'Stretched',i,`${pct(i.parabolic.gap)} above its 150-day EMA (${i.parabolic.asof}). Flag only, score unchanged.`]));
  const PS=DATA.parabolic&&DATA.parabolic.summary;
  const rules=[
    ['Band change','Any model you follow moves band month on month',1],
    ['Entry trigger','Score crosses down through 35 (into Buy) or 20 (Strong buy)',1],
    ['Exit trigger','Score crosses up through 65 (Trim) or 80 (Exit) on something you hold',1],
    ['3-month drift','Score moves the same way three months running (early warning before a band change)',1],
    ['Staging rule','Score in Buy but the macro filter is above 65: stage entries',1],
    ['Disagreement','Two models on the same asset differ by 10+ points',1],
    ['Stale input','An input is older than 35 days, or the monthly run failed',1],
    ['Concentration','A position already above its cap (e.g. Bitcoin >5%) gets a Buy',0],
    ['Thematic froth','AMFI sectoral/thematic froth reaches 80+ (top fifth of its history): flags the size indices, CPSE, Defence and Infra',1],
    ['Parabolic move',`Price 70%+ above its 150-day EMA (50%+ = Stretched). Daily, ${PS?PS.covered+' assets':'when data is available'}. A late-stage warning, not a sell signal: see the back-test below.`,1],
  ];
  const BT=PS&&PS['6m']&&items.some(i=>i.parabolic)?`<div class="card" style="grid-column:1/-1"><h2>Parabolic-move back-test</h2><p class="hint">Every time an asset first closed 70%+ above its 150-day EMA in the last ~10 years of daily data (Yahoo Finance), and what the price did next. Rule from the <a href="#knowledge/sector-rotation-7-indian-bull-runs">sector rotation note</a>.</p>
  <div class="kv" style="max-width:640px"><div>Episodes</div><div>${PS.episodes} across ${PS.assets_with_episodes} of ${PS.covered} assets</div>${['3m','6m','12m'].filter(h=>PS[h]).map(h=>`<div>${h.replace('m',' months')} later</div><div>median ${PS[h].median>0?'+':''}${pct(PS[h].median)}; lower in ${pct(PS[h].share_lower)} of ${PS[h].n} cases</div>`).join('')}<div>Firing now</div><div>${PS.parabolic_now.length?PS.parabolic_now.map(k=>byId[k]?byId[k].name:k).join(', '):'None'}${PS.stretched_now.length?` · Stretched: ${PS.stretched_now.map(k=>byId[k]?byId[k].name:k).join(', ')}`:''}</div></div>
  <p class="hint" style="margin-top:10px">Read it as: prices usually kept rising for months after the rule fired, but with deep swings, so it marks a late, volatile stage rather than a top. That is why it stays a flag and does not move scores.</p></div>`:'';
  const AM=DATA.amfi;
  if(AM&&AM.froth>=80)AM.applies_to.forEach(id=>{if(byId[id]&&items.includes(byId[id]))fired.push(['Thematic froth',byId[id],`AMFI sectoral/thematic froth ${AM.froth}/100 (${AM.month}); adds to this index's Sector cycle score`])});
  const FR=AM&&AM.history&&AM.history.length&&items.some(i=>AM.applies_to.includes(i.id))?(()=>{const W=640,H=120,h=AM.history,x=k=>8+k/(h.length-1)*(W-16),y=v=>H-14-(v/100)*(H-28);
    const yr=h.map((p,k)=>[p[0],k]).filter(p=>p[0].endsWith('-01'));
    return `<div class="card" style="grid-column:1/-1"><h2>Thematic-fund froth (AMFI)</h2><p class="hint">How hard money is chasing sectoral/thematic funds, against its own history since 2019 (0 = quiet, 100 = most intense). Feeds the Sector cycle bucket of the size indices, CPSE, Defence and Infra (indicator S4). Latest: <b>${AM.froth}</b> for ${AM.month}; peak ${AM.peak[1]} in ${AM.peak[0]}.</p>
    <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px" role="img" aria-label="Thematic-fund froth history, latest ${AM.froth}"><rect x="8" y="${y(100)}" width="${W-16}" height="${y(80)-y(100)}" fill="var(--b6)" opacity=".12"/><line x1="8" x2="${W-8}" y1="${y(50)}" y2="${y(50)}" stroke="var(--line-2)" stroke-dasharray="3 3"/><polyline fill="none" stroke="var(--ink)" stroke-width="1.5" points="${h.map((p,k)=>`${x(k).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>${yr.map(([m,k])=>`<text x="${x(k)}" y="${H-2}" font-size="10" text-anchor="middle" style="fill:var(--ink-3)">${m.slice(0,4)}</text>`).join('')}</svg>
    <p class="hint" style="margin-top:6px">Back-check 2019–2026: after months in the top third, the Nifty 500 returned a median +4–5% over 12 months, vs +15–28% after the bottom third. One cycle only. <a href="#knowledge/sector-froth-signals">Evidence</a></p></div>`})():'';
  return `<div class="grid g2">
  <div class="card"><h2>Triggered by the ${MONTHNAME} run</h2><p class="hint">Computed from the logs. In the real build these would arrive as a digest after the monthly refresh on the 3rd.</p>
  ${fired.length?'':'<div class="empty">Nothing triggered in this tab.</div>'}<table><tr><th>Rule</th><th>Signal</th><th>Why</th></tr>${fired.map(f=>`<tr class="row" data-id="${f[1].id}" style="display:table-row"><td><span class="pill">${f[0]}</span></td><td><b>${esc(f[1].name)}</b> ${f[1].score}</td><td>${esc(f[2])}</td></tr>`).join('')}</table></div>
  <div class="card"><h2>Alert rules (proposed)</h2><p class="hint">Toggles are illustrative. "On something you hold" needs your holdings, see Design notes.</p>
  <table>${rules.map(r=>`<tr><td><span class="pill ${r[2]?'on':''}">${r[2]?'On':'Off'}</span></td><td><b>${r[0]}</b><br><span style="color:var(--ink-2)">${r[1]}</span></td></tr>`).join('')}</table></div>${BT}${FR}</div>`;
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
  snapshot:{t:'Snapshot',sub:'Every asset class on one 1–100 scale: where the cheap and rich readings are today.',scope:()=>true,
    notes:['market-legends-council-2026-11-23','sector-investing-playbook','sector-rotation-research-evidence','board-backlog']},
  india:{t:'Indian equities',sub:'Three cuts: by market cap (Nifty 50, large, mid and small caps), by sector, and by individual stock (Nifty 50 and your watchlist).',scope:i=>i.id==='NIFTY50'||['sectors','factors','stocks'].includes(i.model),
    notes:['market-legends-council-2026-11-23','watchlist-analysis-2026-11','sector-investing-playbook','india-sector-facts-2016-2026','sector-froth-signals','valuing-cyclical-sectors','sector-rotation-7-indian-bull-runs','flat-markets-are-not-dead-markets','identifying-winning-sectors']},
  global:{t:'International',sub:'The US first, then 20 more markets, all scored for an INR investor over five years.',scope:i=>i.model==='global',
    notes:['sector-rotation-research-evidence','sector-rotation-economic-cycle-schwab']},
  commod:{t:'Commodities',sub:'Gold, silver, Brent crude and copper.',scope:i=>i.id==='GOLD'||i.model==='commodities',
    notes:['valuing-cyclical-sectors','board-backlog']},
  crypto:{t:'Crypto',sub:'Bitcoin, with its 5% portfolio cap and staging rule.',scope:i=>i.model==='crypto',notes:['board-backlog']},
  fixed:{t:'Fixed income',sub:'Bonds, deposits and cash-like carry, with yields next to scores.',scope:i=>['bonds','carry'].includes(i.model),notes:[]},
  realestate:{t:'Real estate',sub:'Listed REITs and InvITs, and housing by city.',scope:i=>['reits','property'].includes(i.model),notes:[]},
};
/* Tools shown on each tab. The other views (finder, map, alerts, changes, notes) still exist in TOOLVIEW; add them back here to show them. */
const TOOLS=[['','Overview'],['trends','Trends']];
const tabOf=i=>Object.keys(TABS).find(k=>k!=='snapshot'&&TABS[k].scope(i))||'snapshot';
const inTab=t=>ALL_ITEMS.filter(i=>!i.wide&&TABS[t].scope(i));   // headline readings only
const toolOK=(t,k)=>k!=='trends'||SERIES_ALL.some(([id])=>TABS[t].scope(byId[id]));

/* ---------- shared visual pieces ---------- */
const tint=(v,p=34)=>v==null?'transparent':`color-mix(in srgb, ${bcol(v)} ${p}%, var(--surface))`;
const fmtPct=(x,d=0)=>x==null?'—':(x>0?'+':'')+(x*100).toFixed(d)+'%';
const ddNow=i=>i&&i.drawdown?i.drawdown.now:null;
const ddTxt=i=>{const d=ddNow(i);return d==null?'—':d>-0.005?'at high':Math.round(d*100)+'%'};
function gauge(s,W=220,lab=false){const x=v=>2+(v-1)/99*(W-4);
  return `<svg class="gauge" width="${W}" height="${lab?28:16}" viewBox="0 0 ${W} ${lab?28:16}" style="max-width:100%;height:auto" aria-hidden="true">${BANDS.map(b=>`<rect x="${x(Math.max(1,b[1]))}" y="6" width="${Math.max(1,x(b[2])-x(Math.max(1,b[1]))-1.5)}" height="6" rx="2" fill="var(${b[3]})"/>`).join('')}${s!=null?`<path d="M${x(s)-5},0 L${x(s)+5},0 L${x(s)},6 Z" fill="var(--ink)"/><rect x="${x(s)-1}" y="5" width="2" height="8" fill="var(--ink)"/>`:''}${lab?`<text x="2" y="26">1 cheap</text><text x="${W-2}" y="26" text-anchor="end">100 rich</text>`:''}</svg>`}
function bandMix(list,h=10){const c=BANDS.map(b=>list.filter(i=>bandOf(i.score)===b).length);
  return `<div class="mix" style="height:${h}px" role="img" aria-label="${c.map((n,k)=>BANDS[k][0]+' '+n).join(', ')}">${c.map((n,k)=>n?`<i style="flex:${n};background:var(${BANDS[k][3]})" title="${BANDS[k][0]}: ${n}"></i>`:'').join('')}</div>`}
function hc(v,txt){return `<td class="hc" style="background:${tint(v,40)}">${txt??(v==null?'—':Math.round(v))}</td>`}
function flagIcon(i){const f=[];if(i.flags&&/guard/.test(i.flags))f.push('⚑');else if(i.flags)f.push('<span title="model note" style="color:var(--ink-3)">ⓘ</span>');if(i.parabolic&&i.parabolic.status!=='Normal')f.push('<span class="pill">'+i.parabolic.status+'</span>');return f.join(' ')}
function heatTile(i,sub,v){const val=v===undefined?i.score:v;return `<div class="ht" data-id="${i.id}" role="button" tabindex="0" style="background:${tint(val,46)};border-color:${bcol(val)}" aria-label="${esc(i.name)} ${i.score}"><div class="htn">${esc(i.name.replace(/^Nifty (India )?/,'').replace(/ Ltd\.?$/,''))}</div><div class="hts"><b>${i.score.toFixed(0)}</b><span>${sub||''}</span></div></div>`}
function areaTile(t,i,label,extra){const list=inTab(t);return `<a class="at" href="#${t}" style="border-top-color:${bcol(i?i.score:null)}"><div class="atl">${TABS[t].t}</div><div class="atv">${i?i.score.toFixed(0):'—'}<span>${i?chip(i.score):''}</span></div><div class="ats">${esc(label)}</div>${gauge(i?i.score:null,180)}${bandMix(list,6)}<div class="ats">${list.length} reading${list.length>1?'s':''}${extra?' · '+extra:''}</div></a>`}
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
/* dot chart: one row per item, band-shaded 1–100 axis, optional second marker */
function dotChart(id,rows,o={}){const el=document.getElementById(id);if(!el||el.clientWidth<80)return;
  const W=el.clientWidth,L=Math.min(o.L||190,W*.42),R=o.R??60,rh=30,T=20;const x=v=>L+(v-1)/99*(W-L-R);
  let s=`<svg width="${W}" height="${T+rh*rows.length+4}" role="group" aria-label="${esc(o.label||'Scores on the 1 to 100 scale')}">`;
  BANDS.forEach((b,k)=>s+=`<rect x="${x(Math.max(1,b[1]))}" y="${T-4}" width="${x(b[2])-x(Math.max(1,b[1]))}" height="${rh*rows.length}" fill="var(${b[3]})" opacity="${k===3?.14:k===0||k===5?.07:.1}"/>${x(b[2])-x(Math.max(1,b[1]))>b[0].length*6+6?`<text x="${(x(Math.max(1,b[1]))+x(b[2]))/2}" y="11" text-anchor="middle">${b[0]}</text>`:''}`);
  rows.forEach((r,k)=>{const cy=T+k*rh+rh/2-2;
    s+=`<g class="dot" data-id="${r.id}" tabindex="0" role="button" aria-label="${esc(r.label)} ${r.v}" style="cursor:pointer"><rect x="0" y="${cy-rh/2+2}" width="${W}" height="${rh}" fill="transparent"/><line x1="0" x2="${W}" y1="${cy+rh/2-2}" y2="${cy+rh/2-2}" stroke="var(--line)"/><text x="0" y="${cy+4}" style="fill:var(--ink);font-size:12px">${esc(r.label.length>30?r.label.slice(0,28)+'…':r.label)}</text>`;
    if(r.v2!=null)s+=`<line x1="${x(r.v)}" x2="${x(r.v2)}" y1="${cy}" y2="${cy}" stroke="var(--ink-3)" stroke-width="2"/><circle cx="${x(r.v2)}" cy="${cy}" r="5" fill="var(--surface)" stroke="var(--ink)" stroke-width="1.8"/>`;
    s+=`<circle cx="${x(r.v)}" cy="${cy}" r="7" fill="${bcol(r.v)}" stroke="var(--ink)" stroke-width="1.3"/><text x="${W-R+8}" y="${cy+4}" style="fill:var(--ink);font-weight:600">${r.right??r.v.toFixed(1)}</text></g>`});
  el.innerHTML=s+'</svg>';bindDots(el)}
/* scatter: x/y from item fields, colour = score band */
function scatter(id,pts,o){const el=document.getElementById(id);if(!el||el.clientWidth<80)return;
  const W=el.clientWidth,H=Math.min(360,Math.max(240,W*.5)),L=46,R=14,T=14,B=36;
  const xs=pts.map(p=>p.x),ys=pts.map(p=>p.y);const pad=(a,b)=>{const d=(b-a)||1;return [a-d*.08,b+d*.08]};
  const [x0,x1]=o.xr||pad(Math.min(...xs),Math.max(...xs)),[y0,y1]=o.yr||pad(Math.min(...ys),Math.max(...ys));
  const X=v=>L+(v-x0)/(x1-x0)*(W-L-R),Y=v=>T+(y1-v)/(y1-y0)*(H-T-B);
  let s=`<svg width="${W}" height="${H}" role="group" aria-label="${esc(o.label)}">`;
  if(o.xBands)BANDS.forEach((b,k)=>{const a=Math.max(x0,Math.max(1,b[1])),c=Math.min(x1,b[2]);if(c>a)s+=`<rect x="${X(a)}" y="${T}" width="${X(c)-X(a)}" height="${H-T-B}" fill="var(${b[3]})" opacity="${k===3?.12:.08}"/>`});
  const tk=(a,b,n=5)=>{const st=(b-a)/n;return [...Array(n+1)].map((_,k)=>a+st*k)};
  tk(y0,y1).forEach(v=>s+=`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${L-6}" y="${Y(v)+4}" text-anchor="end">${o.yf?o.yf(v):v.toFixed(1)}</text>`);
  tk(x0,x1).forEach(v=>s+=`<text x="${X(v)}" y="${H-B+14}" text-anchor="middle">${o.xf?o.xf(v):v.toFixed(0)}</text>`);
  if(o.yRef!=null)s+=`<line x1="${L}" x2="${W-R}" y1="${Y(o.yRef)}" y2="${Y(o.yRef)}" stroke="var(--ink-3)" stroke-dasharray="4 3"/><text x="${W-R}" y="${Y(o.yRef)-4}" text-anchor="end">${esc(o.yRefL||'')}</text>`;
  s+=`<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">${esc(o.xl)}</text><text transform="translate(12,${(T+H-B)/2}) rotate(-90)" text-anchor="middle">${esc(o.yl)}</text>`;
  const placed=[];const fits=(x0,y0,w)=>{const r=[x0,y0-10,x0+w,y0+3];if(placed.some(q=>!(r[2]<q[0]||r[0]>q[2]||r[3]<q[1]||r[1]>q[3])))return false;placed.push(r);return true};
  pts.forEach(p=>{if(!p.lab)return;const lx=X(p.x),flip=lx>W-150,w=p.lab.length*6.2,x0=flip?lx-9-w:lx+9;if(!fits(x0,Y(p.y)+4,w))p.lab=''});
  pts.forEach(p=>{const i=byId[p.id];const lx=X(p.x),flip=lx>W-150;s+=`<g class="dot" data-id="${p.id}" tabindex="0" role="button" aria-label="${esc(i.name)}"><circle cx="${lx}" cy="${Y(p.y)}" r="11" fill="transparent"/><circle cx="${lx}" cy="${Y(p.y)}" r="6.5" fill="${bcol(i.score)}" stroke="var(--ink)" stroke-width="1.2"/>${p.lab?`<text x="${flip?lx-9:lx+9}" y="${Y(p.y)+4}" text-anchor="${flip?'end':'start'}" style="fill:var(--ink);font-size:12px">${esc(p.lab)}</text>`:''}</g>`});
  el.innerHTML=s+'</svg>';bindDots(el)}
/* small horizontal bars */
function hbars(rows,max,fmt){return `<div class="hb">${rows.map(r=>`<div class="hbr" data-id="${r.id}" role="button" tabindex="0"><span class="hbn">${esc(r.label)}</span><span class="hbt"><i style="width:${Math.max(2,100*r.v/max)}%;background:${bcol(r.c)}"></i></span><span class="hbv">${fmt(r.v)}</span></div>`).join('')}</div>`}

/* ---------- tab overviews ---------- */
let OV_DRAW=[];   // charts drawn after the HTML is in place (and again on resize)
/* Snapshot opens with a heat map of the asset-class model: one tile per asset class, linking to its tab. */
const AC_TAB={'Indian equity':'india','Foreign equity':'global','Indian bonds':'fixed','Foreign bonds':'fixed','Cash':'fixed','Precious metals':'commod','Real estate':'realestate','Crypto':'crypto'};
function acTile(a){const t=AC_TAB[a.family]||'snapshot',tilt=String(a.tilt||'').replace(/\s*\(.*\)$/,'');
  return `<a class="ht" href="#${t}" style="background:${tint(a.score,46)};border-color:${bcol(a.score)};text-decoration:none;color:var(--ink)" aria-label="${esc(a.name)}, score ${a.score}, ${bandOf(a.score)[0]}" title="${esc(a.name)}${a.drivers?' · '+esc(a.drivers):''}">
    <div class="htn">${esc(String(a.name).replace(/\s*\(.*\)$/,''))}</div><div class="hts"><b>${Math.round(a.score)}</b><span>${bandOf(a.score)[0]}</span></div>
    <div class="tag" style="white-space:normal">${esc(tilt)}${a.yield_?` · yield ${a.yield_}%`:''}${a.own!=null?` · full model ${Math.round(a.own)}`:''}</div></a>`}
function ovSnapshot(){
  const reits=inTab('realestate').filter(i=>i.model==='reits').sort((a,b)=>a.score-b.score);const rm=reits[Math.floor(reits.length/2)];
  const ac=[...(DATA.assetClasses||[])].sort((a,b)=>a.score-b.score);
  OV_DRAW=[];
  return `<section class="card" style="margin-bottom:14px"><h2>Asset classes: heat-map</h2><p class="hint">Cheapest to richest on the asset-class model (valuation, five-year view). Each tile shows the suggested tilt; "full model" is the dedicated model's score with timing and macro added. Click a tile to open its tab.</p>
    <div class="heat ac">${ac.map(acTile).join('')}</div></section>
  <div class="tiles7">
    ${areaTile('india',byId.NIFTY50,'Nifty 50')}${areaTile('global',byId.GLB_SP500,'S&P 500 (US)')}${areaTile('commod',byId.GOLD,'Gold')}${areaTile('crypto',byId.BTC,'Bitcoin')}
    ${areaTile('fixed',byId.FI_GSEC_10Y,'10-yr G-sec',byId.FI_GSEC_10Y?`yield ${byId.FI_GSEC_10Y.meta['Yield %']}%`:'')}${areaTile('realestate',rm,'REIT median: '+(rm?rm.name.split(' (')[0]:''))}
  </div>`;
}
/* one-line read at the top of each tab: lean in (≤35) / lean out (>65), from the scores */
const shortName=n=>String(n).replace(/ \(.*\)$/,'').replace(/ Ltd\.?$/,'');
function verdictLine(t){let lin,lout,hold;
  if(t==='snapshot'){const ac=DATA.assetClasses||[];
    lin=ac.filter(a=>/^Overweight/.test(a.tilt||'')).sort((a,b)=>a.score-b.score);lout=ac.filter(a=>/^Underweight/.test(a.tilt||'')).sort((a,b)=>b.score-a.score);hold=ac.length-lin.length-lout.length}
  else{let l=inTab(t).filter(i=>i.score!=null&&!notInvestable(i)&&i.model!=='stocks');
    lin=l.filter(i=>i.score<=35).sort((a,b)=>a.score-b.score);lout=l.filter(i=>i.score>65).sort((a,b)=>b.score-a.score);hold=l.length-lin.length-lout.length}
  const nm=x=>x.slice(0,4).map(i=>byId[i.id]?`<a href="#" data-id="${esc(i.id)}" class="vlink">${esc(shortName(i.name))}</a>`:esc(shortName(i.name))).join(', ')+(x.length>4?` +${x.length-4}`:'');
  return `<div class="verdict"><span><b>Lean in:</b> ${lin.length?nm(lin):'nothing cheap enough'}</span><span><b>Hold:</b> ${hold}</span><span><b>Lean out:</b> ${lout.length?nm(lout):'nothing rich enough'}</span><span class="tag">${t==='snapshot'?'From the asset-class model\'s tilts.':'Lean in = score 35 or lower; lean out = above 65.'}</span></div>`}
let indState={heat:'score',sec:'all',stockView:'grid',uni:'n50',view:'cap',valMax:50,cell:null,dvAll:false};
try{const v=localStorage.getItem('eeb-india-view');indState.view={top:'cap',bottom:'stock'}[v]||(['cap','sector','stock'].includes(v)?v:'cap')}catch(e){}
const SIZE_IDS=['SEC_NIFTY500','SEC_NEXT50','SEC_MIDSELECT','SEC_MIDCAP150','SEC_SMALLCAP250'];
/* value setups (scripts/fetch_parabolic.py price_setup): how a stock's price got where it is */
const SETUPS=[['short','Short-term drawdown','Fell 15% or more from its 3-month high'],['long','Long-term drawdown','30% or more below its 5-year high, and that high is over a year old'],
  ['consol','Consolidation','6 months or more inside a 25% high-to-low band'],['base','Multi-year base','Price has compounded 7% a year or less (about a fixed deposit) for 5 years or more']];
const SETUP_NAME=Object.fromEntries(SETUPS.map(s=>[s[0],s[1]]));
const pc=(x,d=0)=>x==null?'—':(x>0?'+':'')+(x*100).toFixed(d)+'%';
const hasSetup=(i,k)=>!!(i.setup&&i.setup.types&&i.setup.types.includes(k));
const growing=i=>{const g=i.growth;return !!g&&((g.eps_cagr!=null&&g.eps_cagr>0)||(g.pg5!=null&&g.pg5>0))};
function setupNote(i,k){const s=i.setup;if(!s)return '';
  return k==='short'?`${pc(s.dd_3m)} from 3-month high`:k==='long'?`${pc(s.dd_5y)} from 5-yr high (${s.years_below_5y_high} yrs ago)`:
    k==='consol'?`${s.consol_months} months in a ${Math.round(s.consol_range*100)}% band`:`flat ${s.flat_years} yrs · 5-yr price ${pc(s.cagr&&s.cagr['5'],1)}/yr`}
const seqBg=(n,max)=>n?`color-mix(in srgb, var(--focus) ${Math.round(12+68*n/Math.max(1,max))}%, var(--surface))`:'transparent';
const seqInk=(n,max)=>n&&12+68*n/Math.max(1,max)>55?'#fff':'var(--ink)';
function oppTile(i,k){const g=i.growth||{};return `<div class="ht" data-id="${i.id}" role="button" tabindex="0" style="background:${tint(i.score,46)};border-color:${bcol(i.score)}" aria-label="${esc(i.name)}, score ${i.score}">
  <div class="htn">${i.watch?'★ ':''}${esc(i.meta.Ticker)} <span class="tag">${esc(i.name.replace(/ Ltd\.?$/,''))}</span></div>
  <div class="hts"><b>${i.score.toFixed(0)}</b></div><div style="display:flex;flex-wrap:wrap;gap:3px;margin:2px 0">${(i.setup.types||[]).map(t=>`<span class="pill sp">${{short:'Short-term',long:'Long-term',consol:'Consolidation',base:'Multi-year base'}[t]}</span>`).join('')}</div>
  <div class="tag" style="white-space:normal">${esc(k?setupNote(i,k):(i.setup.types||[]).map(t=>setupNote(i,t)).join(' · '))}${g.eps_cagr!=null?` · EPS ${g.eps_cagr>0?'+':''}${g.eps_cagr}%/yr`:''}</div></div>`}
function watchCard(i){const s=i.setup,g=i.growth||{};
  return `<div class="at" data-id="${i.id}" role="button" tabindex="0" style="border-top-color:${bcol(i.score)}"><div class="atl">★ ${esc(i.meta.Ticker)} · ${esc(i.meta.Universe)}</div>
  <div class="atv">${i.score==null?'—':i.score.toFixed(0)}<span>${i.score==null?'':chip(i.score)}</span></div><div class="ats"><b>${esc(i.name)}</b></div>${gauge(i.score,200)}
  <div class="ats">${s?(s.types.length?s.types.map(t=>'<b>'+SETUP_NAME[t]+'</b>: '+esc(setupNote(i,t))).join('<br>'):'No value setup right now'):'Price setup arrives with the next daily refresh'}</div>
  <div class="ats">Price ${s&&s.cagr?`5-yr ${pc(s.cagr['5'],1)}/yr · 10-yr ${pc(s.cagr['10'],1)}/yr`:`5-yr ${g.px5!=null?g.px5+'%/yr':'—'}`} · EPS ${g.eps_cagr!=null?(g.eps_cagr>0?'+':'')+g.eps_cagr+'%/yr':'—'}${g.eps&&g.eps.length?` (${g.eps.length} yrs)`:''}</div>
  <div class="ats">PE ${i.meta.PE??'—'} vs sector ${i.meta['Sector PE']??'—'} · ROE 5-yr ${g.roe5??'—'}%</div></div>`}
function ovIndia(){
  const v=indState.view;
  const views=[['cap','Market cap','Nifty 50 → large, mid and small caps'],['sector','Sectors','Heat map, table, stock-by-stock check'],['stock','Stocks',STOCK_FOCUS?'Your watchlist · best value pick per sector':'Value setups, 5-year deep value, screener']];
  const cur=views.find(x=>x[0]===v)||views[0];
  const sw=`<div class="vbar"><div class="vsw seg" role="tablist" aria-label="Indian equities view">${views.map(([k,t,s])=>`<button role="tab" aria-selected="${v===k}" class="${v===k?'on':''}" data-v="${k}" title="${esc(s)}">${t}</button>`).join('')}</div><span class="tag">${esc(cur[2])}</span></div>`;
  return sw+(v==='cap'?ovIndiaCap():v==='sector'?ovIndiaSector():ovIndiaBottom());
}
const relB=i=>(i.buckets||{})['Relative vs Nifty'];
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
function ovIndiaCap(){
  const n=byId.NIFTY50,AM=DATA.amfi,SR=DATA.size_rotation;
  const size=SIZE_IDS.map(k=>byId[k]).filter(Boolean);
  const draw=[()=>dotChart('sizec',[n,...size].map(i=>({id:i.id,label:i.name.replace(' (benchmark)',''),v:i.score,v2:relB(i)}) ),{label:'Size indices, absolute and relative'}),
           ];
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
  return `<h3 class="step"><span>1</span>The market and its size bands</h3><div class="grid g2" style="margin-bottom:14px">
    <section class="card hero" style="border-top-color:${bcol(n.score)}"><h2>Nifty 50</h2><div class="herorow"><div class="big">${n.score}</div><div>${chip(n.score)}<div class="tag">${esc(n.signal)}</div></div></div>${gauge(n.score,320,true)}
      <div class="bk">${Object.entries(n.buckets).filter(([k,v])=>v!=null).map(([k,v])=>`<div style="background:${tint(v,40)}"><span>${k==='Filter'?'Macro':k}</span><b>${Math.round(v)}</b></div>`).join('')}<div style="background:${tint(ddNow(n)==null?null:50)}"><span>From high</span><b>${ddTxt(n)}</b></div>${AM?`<div style="background:${tint(AM.froth,40)}"><span>Fund froth</span><b>${AM.froth}</b></div>`:''}</div>
      <button class="btn" data-id="NIFTY50" style="margin-top:10px">Open Nifty 50 details</button></section>
    <section class="card"><h2>Size: large → small caps</h2><p class="hint">Filled dot: the index's own score. Ring: score relative to the Nifty 50 (low = cheaper than the market).</p><div id="sizec"></div></section></div>
  ${heatBlock('Size indices: heat-map','Large to small caps, cheapest first. Colour shows the band of what you colour by.',[n,...size],['score','rel','dd'])}
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
    <span class="seg heatseg" aria-label="Colour by">${modes.map(k=>`<button data-v="${k}" class="${k===m?'on':''}">${HEAT_MODES[k][0]}</button>`).join('')}</span></div>
    <div class="heat${o.cls?' '+o.cls:''}">${l.map(i=>heatTile(i,(o.star&&i.watch?'★ ':'')+hsub(i)+(i.flags&&/guard/.test(i.flags)?' ⚑':''),hv(i))).join('')}</div>
    ${m==='dd'?'<div class="tag" style="margin-top:6px">Distance from high: blue = far below its 10-year high, red = at or near it. Grey tiles have no daily price history.</div>':''}</section>`}
function ovIndiaSector(){
  const sectors=ALL_ITEMS.filter(i=>i.model==='sectors'&&!SIZE_IDS.includes(i.id));
  OV_DRAW=[];
  return `<h3 class="step">Sectors at a glance</h3>
  ${heatBlock('Sectors: heat-map','Cheapest to richest. Colour shows the band of what you colour by.',sectors,['score','rel','dd'])}
  <h3 class="step">The detail</h3>
  <section class="card" style="margin-bottom:14px"><h2>Sectors: table</h2><p class="hint">Click a column to sort; click a row for the full panel. ⚑ = peak-earnings guard on; ⓘ = model note.</p>
    ${sortTable('sec',[C.name,C.score,{k:'rel',l:'Relative',num:1,get:relB,cell:i=>hc(relB(i))},C.b('Valuation'),C.b('Sector cycle','Cycle'),C.b('Timing'),C.b('Filter','Macro'),C.dd,C.flags],sectors,{k:'score',dir:1,keep:['name','score','rel']})}</section>
  <h3 class="step">Hand-off to stocks</h3>
  <section class="card"><h2>Does the sector call hold stock by stock?</h2><p class="hint">Big dot: the sector index's score. Small dots: its Nifty 50 and watchlist stocks. Diamond: their median. Right-hand column: <b>gap</b> = stock median minus the index score (negative: the stocks are cheaper than the index suggests; ⚑ when 10 or more points apart) · <b>spread</b> = richest stock minus cheapest (wide: pick stocks, don't buy the whole sector). Sectors with the biggest gap come first. Open the Stocks view for the names.</p><div id="sxsvg"></div></section>`;
}
/* Stocks view focus: show only the watchlist and the per-sector value picks.
   Set to false to bring back the full view (setup heat map, 5-year deep value, screener). */
const STOCK_FOCUS=true;
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
  return `<h3 class="step">Your watchlist</h3>
  <section class="card" style="margin-bottom:14px"><p class="hint">Cheapest first. Click a row for the full panel.${watchMissing.length?` Not scored yet: ${watchMissing.map(w=>esc(w.name)).join(', ')}.`:''}</p>
    ${sortTable('wl',[{k:'name',l:'Name',get:i=>i.name,fmt:nm},{k:'ind',l:'Sector',get:IN},C.score,pe,eps,
      {k:'roe',l:'ROE 5-yr',num:1,get:i=>(i.growth||{}).roe5,fmt:i=>(i.growth||{}).roe5!=null?(i.growth||{}).roe5+'%':'—'},
      {k:'d3',l:'From 3-mo high',num:1,get:i=>i.setup?i.setup.dd_3m:null,fmt:i=>i.setup?pc(i.setup.dd_3m):'—'},why],watch,{k:'score',dir:1,keep:['name','score','d3']})}</section>
  ${heatBlock('Nifty 50 and watchlist: heat-map','Every stock on the board, cheapest first. ★ = on your watchlist. Click a tile for the full panel.',all,['score','val','dd'],{cls:'sm',star:1})}
  <h3 class="step">Value opportunities: the best in each sector</h3>
  <section class="card"><p class="hint">From the Nifty 50: stocks scoring 50 or lower that show a value setup now, best one per sector (a second only if it scores ${PICK_SECOND} or lower), cheapest first. Falling knives the model vetoes are left out. Hover a setup for the detail.${asof?` Prices to ${esc(String(asof.setup.asof).slice(0,10))}.`:''}</p>
    ${picks.length?sortTable('vp',[{k:'name',l:'Name',get:i=>i.name,fmt:nm},{k:'ind',l:'Sector',get:IN},C.score,pe,eps,why],picks,{k:'score',dir:1,keep:['name','score','why']})
      :'<div class="empty">The value setups come from the daily price check and appear after its next run.</div>'}
    ${short.length?`<details style="margin-top:10px"><summary class="tag xnote">Note: top 10 on short-term reasons (fell 15%+ from the 3-month high)</summary><div class="tag" style="white-space:normal;margin-top:6px">${short.map((i,k)=>`${k+1}. ${esc(i.name.replace(/ Ltd\.?$/,''))} (${i.score.toFixed(0)}, ${pc(i.setup.dd_3m)})`).join(' · ')}</div></details>`:''}</section>`;
}
function ovIndiaBottom(){
  if(STOCK_FOCUS)return ovStockFocus();
  const all=ALL_ITEMS.filter(i=>i.model==='stocks'&&i.score!=null);
  const stocks=all.filter(i=>indState.uni==='all'||!i.wide);
  const withSetup=all.filter(i=>i.setup);
  const valOK=i=>indState.valMax>=100||i.score<=indState.valMax;
  const opp=withSetup.filter(i=>valOK(i)&&i.setup.types.length);
  const IN=i=>i.meta.Industry||i.meta.Sector;
  const secNames=[...new Set(all.map(IN))].filter(Boolean);
  const cnt=(sec,k)=>opp.filter(i=>(!sec||IN(i)===sec)&&hasSetup(i,k)).length;
  const rows=secNames.map(sec=>[sec,SETUPS.map(s=>cnt(sec,s[0]))]).filter(r=>r[1].some(Boolean)).sort((a,b)=>b[1].reduce((x,y)=>x+y,0)-a[1].reduce((x,y)=>x+y,0));
  const max=Math.max(1,...rows.flatMap(r=>r[1]));
  const cell=indState.cell;   // [sector|null, setup|null]
  const picked=opp.filter(i=>(!cell||!cell[0]||IN(i)===cell[0])&&(!cell||!cell[1]||hasSetup(i,cell[1]))).sort((a,b)=>a.score-b.score);
  const cellTxt=!cell?'every sector and setup':`${cell[0]||'all sectors'} · ${cell[1]?SETUP_NAME[cell[1]].toLowerCase():'any setup'}`;
  const watch=ALL_ITEMS.filter(i=>i.watch).sort((a,b)=>(a.score??999)-(b.score??999));
  const watchMissing=(DATA.watchlist||[]).filter(w=>!byId['STK_'+w.ticker]);
  const vlabel=indState.valMax===35?'Buy or better (score 35 or lower)':indState.valMax===50?'Accumulate or better (score 50 or lower)':'any score';
  // 5-year deep value: price flat for 5+ years while earnings kept growing
  const dv=withSetup.filter(i=>hasSetup(i,'base')&&growing(i)&&(indState.dvAll||i.score<=50));
  const dvExtra=watch.filter(i=>!dv.includes(i));
  const gap=i=>{const g=i.growth||{},c=i.setup&&i.setup.cagr&&i.setup.cagr['5'];return g.eps_cagr==null||c==null?null:+(g.eps_cagr-c*100).toFixed(1)};
  const cg=k=>({k:'c'+k,l:k+'-yr price',num:1,get:i=>i.setup&&i.setup.cagr?i.setup.cagr[k]:null,fmt:i=>i.setup&&i.setup.cagr?pc(i.setup.cagr[k],1):'—'});
  const noData=!withSetup.length;
  return `${watch.length||watchMissing.length?`<h3 class="step">Your watchlist</h3><div class="tiles3" style="margin-bottom:14px">${watch.map(watchCard).join('')}${watchMissing.map(w=>`<div class="at" style="border-top-color:var(--line-2)"><div class="atl">★ ${esc(w.ticker)} · Watchlist</div><div class="atv">—</div><div class="ats"><b>${esc(w.name)}</b></div><div class="ats">Outside the Nifty 500, so not scored yet. The stock fundamentals fetch (monthly, on the 4th, or run it by hand) adds its inputs; the daily price check adds its setups.</div></div>`).join('')}</div>`:''}
  <h3 class="step"><span>1</span>Where the value is: heat map by setup</h3>
  <section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Value opportunities by what created them</h2>
    <p class="hint">Rows: NSE sector. Columns: how the price got cheap. Each cell counts stocks in the Nifty 500${watch.some(i=>i.meta.Universe==='Watchlist')?' and your watchlist':''} that score ${vlabel} and show that setup; darker = more. A stock can sit in more than one column. Click a cell, a row or a column to list the stocks.</p></div>
    <span class="seg" id="valseg" aria-label="Value filter"><button data-v="35">Buy ≤35</button><button data-v="50">Accumulate ≤50</button><button data-v="100">Any score</button></span></div>
    ${noData?`<div class="empty">The price setups (drawdowns, consolidation, multi-year base) are computed by the daily price check and appear after its next run.</div>`:`
    <div class="tscroll"><table class="hm"><thead><tr><th scope="col"><button class="btn hmc" data-s="" data-k="">All</button></th>${SETUPS.map((s,k)=>`<th scope="col"><button class="btn hmc" data-s="" data-k="${s[0]}" title="${esc(s[2])}">${s[1]}<span class="tag">${cnt(null,s[0])} stocks</span></button></th>`).join('')}</tr></thead>
    <tbody>${rows.map(([sec,c])=>`<tr><th scope="row"><button class="btn hmc" data-s="${esc(sec)}" data-k="">${esc(sec)}</button></th>${c.map((n,k)=>`<td><button class="hmcell${cell&&cell[0]===sec&&cell[1]===SETUPS[k][0]?' on':''}" data-s="${esc(sec)}" data-k="${SETUPS[k][0]}" style="background:${seqBg(n,max)};color:${seqInk(n,max)}" aria-label="${esc(sec)}, ${SETUPS[k][1]}: ${n} stocks" ${n?'':'disabled'}>${n||'·'}</button></td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <div class="hmleg"><span class="tag">Fewer</span><i style="background:${seqBg(1,4)}"></i><i style="background:${seqBg(2,4)}"></i><i style="background:${seqBg(3,4)}"></i><i style="background:${seqBg(4,4)}"></i><span class="tag">More stocks</span>
      <span class="tag" style="margin-left:12px">${SETUPS.map(s=>`<b>${s[1]}</b>: ${s[2].toLowerCase()}`).join(' · ')}</span></div>`}
  </section>
  ${noData?'':`<section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Stocks in ${esc(cellTxt)} (${picked.length})</h2><p class="hint">Cheapest first. Tile colour = band. ★ = on your watchlist.</p></div>${cell?'<button class="btn" id="hmclear">Show all</button>':''}</div>
    <div class="heat opp">${picked.slice(0,30).map(i=>oppTile(i,cell&&cell[1])).join('')}</div>${picked.length>30?`<div class="tag" style="margin-top:6px">Showing the 30 cheapest of ${picked.length}. Click a cell to narrow.</div>`:''}</section>`}
  <h3 class="step"><span>2</span>Five-year horizon: deep value to accumulate</h3>
  <section class="card" style="margin-bottom:14px"><div class="cardhead"><div><h2>Price flat for 5 to 10 years, earnings still growing (${dv.length})</h2>
    <p class="hint">Stocks whose price has compounded 7% a year or less for 5 years or more (about a fixed deposit, dividends not counted) while EPS kept growing, so the multiple has de-rated. <b>Earnings gap</b> = EPS growth minus 5-year price growth, in points a year: the bigger it is, the more the valuation has compressed. ${indState.dvAll?'All scores shown.':'Score 50 or lower only.'} Watchlist names are always listed.</p>
    <p class="hint">Caveat: Yahoo Finance gives 4 to 6 years of annual EPS for most stocks, so "growing" is judged on that window, not on 10 years. Open a stock to check the longer record.</p></div>
    <label class="toggle"><input type="checkbox" id="dvall" ${indState.dvAll?'checked':''}> Include scores above 50</label></div>
    ${noData?`<div class="empty">Needs the price setups from the next daily price check.</div>`:sortTable('dv',[{k:'name',l:'Name',get:i=>i.name,fmt:i=>`${i.watch?'★ ':''}<b>${esc(i.name)}</b>`},{k:'ind',l:'Sector',get:IN},C.score,
      {k:'flat',l:'Flat for',num:1,get:i=>i.setup?i.setup.flat_years:null,fmt:i=>i.setup&&i.setup.flat_years?i.setup.flat_years+' yrs':'—'},cg('5'),cg('10'),
      {k:'eps',l:'EPS growth',num:1,get:i=>(i.growth||{}).eps_cagr,fmt:i=>{const g=i.growth||{};return g.eps_cagr==null?'—':(g.eps_cagr>0?'+':'')+g.eps_cagr+'%/yr'}},
      {k:'gap',l:'Earnings gap',num:1,get:gap,cell:i=>{const v=gap(i);return `<td class="hc" style="background:${v==null?'transparent':seqBg(Math.max(0,Math.min(20,v)),20)};color:${v==null?'var(--ink)':seqInk(Math.max(0,Math.min(20,v)),20)}">${v==null?'—':(v>0?'+':'')+v}</td>`}},
      C.m('PE','PE',1),C.m('Sector PE','Sector PE',1),{k:'roe',l:'ROE 5-yr',num:1,get:i=>(i.growth||{}).roe5,fmt:i=>(i.growth||{}).roe5??'—'},
      {k:'d5',l:'From 5-yr high',num:1,get:i=>i.setup?i.setup.dd_5y:null,fmt:i=>i.setup?pc(i.setup.dd_5y):'—'},
      {k:'st',l:'Setups now',get:i=>i.setup?i.setup.types.length:0,fmt:i=>i.setup?i.setup.types.map(t=>SETUP_NAME[t]).join(', ')||'none':'—'}],[...dv,...dvExtra],{k:'score',dir:1})}</section>
  <h3 class="step"><span>3</span>Screener</h3>
  ${stockScreener(stocks)}`;
}
function stockScreener(stocks){
  const sgroups=[...new Set(stocks.map(i=>i.meta.Sector))].sort();
  const sel=stocks.filter(i=>indState.sec==='all'||i.meta.Sector===indState.sec);
  const byGrp=sgroups.filter(g=>sel.some(i=>i.meta.Sector===g)).map(g=>[g,sel.filter(i=>i.meta.Sector===g).sort((a,b)=>a.score-b.score)]).sort((a,b)=>a[1][0].score-b[1][0].score);
  return `<section class="card"><div class="cardhead"><div><h2>Stocks (${indState.uni==='all'?'Nifty 500 + watchlist':'Nifty 50'}: ${stocks.length})</h2><p class="hint">Grouped by sector, cheapest group first. Colour = band.</p></div>
    <div class="filters" style="margin:0"><label class="sr" for="secsel">Sector</label><select id="secsel" class="btn"><option value="all">All sectors</option>${sgroups.map(g=>`<option ${indState.sec===g?'selected':''}>${esc(g)}</option>`).join('')}</select>
    <span class="seg" id="uniseg"><button data-v="n50">Nifty 50</button><button data-v="all">Nifty 500</button></span> <span class="seg" id="stseg"><button data-v="grid">Heat grid</button><button data-v="table">Table</button></span></div></div>
    ${indState.stockView==='grid'?`<div class="sgrid">${byGrp.map(([g,l])=>`<div class="sg"><div class="sgh">${esc(g)}</div><div class="heat sm">${l.map(i=>heatTile(i,(i.meta.PE?'PE '+i.meta.PE:''))).join('')}</div></div>`).join('')}</div>`
    :sortTable('stk',[C.name,C.m('Sector'),C.score,C.b('Valuation'),C.b('Quality'),C.b('Momentum'),C.m('PE','PE',1),C.m('Sector PE','Sector PE',1),C.dd,C.flags],sel,{k:'score',dir:1})}</section>`;
}
const REGION={'United States':'Americas',Canada:'Americas',Brazil:'Americas',Mexico:'Americas','United Kingdom':'Europe',France:'Europe',Germany:'Europe',Netherlands:'Europe',Italy:'Europe',Spain:'Europe',Poland:'Europe',Turkey:'Europe & Middle East',Russia:'Europe & Middle East','Saudi Arabia':'Europe & Middle East',Japan:'Asia-Pacific',Australia:'Asia-Pacific','South Korea':'Asia-Pacific',China:'Asia-Pacific',India:'Asia-Pacific',Indonesia:'Asia-Pacific',World:'World'};
function ovGlobal(){
  const g=ALL_ITEMS.filter(i=>i.model==='global'),us=['GLB_SP500','GLB_NDX','GLB_RUT'].map(k=>byId[k]).filter(Boolean);
  const er=i=>{const v=(i.meta||{})['Exp. INR return % p.a. (net)'];return v===''||v==null?null:+v};
  const regions=['Americas','Europe','Europe & Middle East','Asia-Pacific','World'].map(r=>[r,g.filter(i=>(REGION[i.meta.Economy]||'Asia-Pacific')===r).sort((a,b)=>a.score-b.score)]).filter(r=>r[1].length);
  OV_DRAW=[];
  return `<section class="card" style="margin-bottom:14px"><h2>By region: heat-map</h2><p class="hint">Cheapest first within each region. Colour = band; the small figure is the expected return a year in INR over five years. Click a tile to open it.</p>${regions.map(([r,l])=>`<div class="grp">${r}</div><div class="heat sm">${l.map(i=>heatTile(i,er(i)!=null?er(i)+'%/yr':'')).join('')}</div>`).join('')}</section>
  <h3 class="step">United States: drill-down</h3>
  <div class="tiles3">${us.map(i=>`<div class="at" data-id="${i.id}" role="button" tabindex="0" style="border-top-color:${bcol(i.score)}"><div class="atl">${esc(i.meta.Economy)}</div><div class="atv">${i.score.toFixed(0)}<span>${chip(i.score)}</span></div><div class="ats"><b>${esc(i.name)}</b></div>${gauge(i.score,200)}<div class="ats">Expected ${er(i)}% a year in INR (${esc(i.meta.Range||'')}) · ${esc(i.action||'')}</div><div class="ats">From high ${ddTxt(i)}</div></div>`).join('')}</div>
  <section class="card"><h2>All markets</h2><p class="hint">Click a column to sort. Expected return is net, in INR, a year over five years.</p>
    ${sortTable('glb',[C.m('Economy'),C.name,C.score,C.b('Valuation'),C.b('Macro'),C.b('Currency'),C.b('Timing'),{k:'er',l:'Exp. INR %/yr',num:1,get:er,fmt:i=>er(i)==null?'—':er(i).toFixed(1)},C.dd],g,{k:'score',dir:1,keep:['m_Economy','name','score','er']})}</section>`;
}
const PKEY={GOLD:'gold_usd',CMD_SILVER:'silver_usd',CMD_BRENT:'brent_usd',CMD_COPPER:'copper_usd_t',BTC:'btc_usd'};
function priceLine(i){const k=PKEY[i.id];if(!k)return '';const run=(DATA.run_prices||{})[k],lp=latestPrice(k);if(!run||!lp)return '';const ch=lp.value/run-1;
  return `<div class="kv"><div>Price at scoring</div><div>${(+run).toLocaleString('en-IN')} ${PRICE_META[k][1]}</div><div>Latest</div><div>${(+lp.value).toLocaleString('en-IN',{maximumFractionDigits:2})} <b>${fmtPct(ch,1)}</b>${Math.abs(ch)>=.05?' <span class="stat due">big move</span>':''}</div></div>`}
function assetCard(i,wide){const P=i.parabolic;return `<section class="card hero" style="border-top-color:${bcol(i.score)}"><div class="cardhead"><h2>${esc(i.name)}</h2>${tierTag(i.tier)}</div>
  <div class="herorow"><div class="big">${i.score}</div><div>${chip(i.score)}<div class="tag">${esc(i.signal)}</div></div></div>${gauge(i.score,wide?420:280,true)}
  <div class="bk">${Object.entries(i.buckets||{}).filter(([k,v])=>v!=null).map(([k,v])=>`<div style="background:${tint(v,40)}"><span>${k==='Filter'?'Macro':k}</span><b>${Math.round(v)}</b></div>`).join('')}
   <div style="background:${tint(ddNow(i)==null?null:Math.max(1,Math.min(100,100+ddNow(i)*200)),30)}"><span>From high</span><b>${ddTxt(i)}</b></div>${P?`<div style="background:${tint(Math.max(1,Math.min(100,50+P.gap*70)),30)}"><span>vs 150-day avg</span><b>${fmtPct(P.gap)}</b></div>`:''}</div>
  ${i.history&&i.history.length>2?`<div class="tag" style="margin-top:8px">Score, last ${Math.min(24,i.history.length)} months</div>${spark(i.history.slice(-24),wide?560:300,wide?110:60)}`:''}
  ${priceLine(i)}${i.action?`<div class="note"><b>Model's action:</b> ${esc(i.action)}</div>`:''}
  <button class="btn" data-id="${i.id}" style="margin-top:8px">Open full details</button></section>`}
function ovCommod(){const l=['GOLD','CMD_SILVER','CMD_BRENT','CMD_COPPER'].map(k=>byId[k]).filter(i=>i&&i.score!=null);
  OV_DRAW=[];
  return `<div class="grid g2">${l.map(i=>assetCard(i)).join('')}</div>`}
function ovCrypto(){const b=byId.BTC;return `<div class="grid g2"><div>${assetCard(b,true)}</div><section class="card"><h2>Rules that come with it</h2>
  <ul class="rules"><li><b>Cap at 5% of the portfolio.</b> Bitcoin's falls have reached ${b.drawdown?pct(b.drawdown.worst):'−80%'} in the last decade.</li><li><b>Stage entries</b> when the macro filter is high (now ${b.buckets.Filter}).</li><li><b>Tax:</b> 31.2% on gains (VDA), no loss set-off.</li><li>Score history before Nov 2026 is reconstructed (±3 points).</li></ul>
  <div class="tag" style="margin-top:8px">Distance from high</div>${b.drawdown?`<div class="ddbar"><i style="width:${Math.min(100,-b.drawdown.now*100)}%"></i></div><div class="tag">${pct(b.drawdown.now)} from its ${b.drawdown.high_date} high · worst ${pct(b.drawdown.worst)} (${b.drawdown.worst_date})</div>`:''}</section></div>`}
function ovFixed(){const bonds=ALL_ITEMS.filter(i=>i.model==='bonds'),carry=ALL_ITEMS.filter(i=>i.model==='carry');
  const y=i=>+((i.meta||{})['Yield %']||0),acIds=['SHORT_DEBT','GSEC_LONG','CORP_AAA','CREDIT_AA','US_TREASURY','CASH'];const acs=DATA.assetClasses.filter(a=>acIds.includes(a.id));
  return `<div class="grid g2" style="margin-bottom:14px"><section class="card"><h2>Yield vs score</h2><p class="hint">Bar length = yield; colour = the model's band (blue = attractive now). Click a bar to open it.</p>${hbars(bonds.sort((a,b)=>y(b)-y(a)).map(i=>({id:i.id,label:i.name.replace(/ \(.*\)/,''),v:y(i),c:i.score})),Math.max(...bonds.map(y)),v=>v.toFixed(2)+'%')}</section>
    <section class="card"><h2>Asset-class view</h2><p class="hint">Valuation-only score for each fixed-income class, with the suggested tilt.</p>${acs.map(a=>`<div class="row" style="cursor:default"><span class="score">${a.score}</span><span class="sw" style="background:${bcol(a.score)}"></span><span class="nm">${esc(a.name)}</span><span class="tag">${esc(a.tilt||'')}${a.yield_!=null?' · '+a.yield_+'%':''}</span></div>`).join('')}</section></div>
  <section class="card" style="margin-bottom:14px"><h2>Bonds and deposits</h2>${sortTable('fi',[C.name,C.score,{k:'y',l:'Yield %',num:1,get:y,fmt:i=>y(i).toFixed(2)},C.b('Valuation'),C.b('Timing'),C.b('Filter','Macro'),{k:'act',l:"Model's action",get:i=>i.action||''}],bonds,{k:'score',dir:1,keep:['name','score','y']})}</section>
  <section class="card"><h2>Cash-like carry</h2><div class="grid g2">${carry.map(i=>`<div class="at" data-id="${i.id}" role="button" tabindex="0" style="border-top-color:${bcol(i.score)}"><div class="atl">${esc(i.name)}</div><div class="atv">${i.score.toFixed(0)}<span>${chip(i.score)}</span></div>${gauge(i.score,200)}<div class="ats">Post-tax ${esc(i.meta['Post-tax yield %'])}% · edge vs liquid ${esc(i.meta['Edge vs liquid (pp)'])} pp</div><div class="ats">${esc(i.action||'')}</div></div>`).join('')}</div></section>`}
function ovRE(){const r=ALL_ITEMS.filter(i=>i.model==='reits'),c=ALL_ITEMS.filter(i=>i.model==='property');const m=(i,k)=>{const v=(i.meta||{})[k];return v===''||v==null?null:+v};
  OV_DRAW=[()=>scatter('rsc',r.filter(i=>m(i,'Post-tax yield %')!=null&&m(i,'Price/NAV')!=null).map(i=>({id:i.id,x:m(i,'Post-tax yield %'),y:m(i,'Price/NAV'),lab:i.name.replace(/ (Real Estate |Office |Business )?(Investment )?(Trust|REIT|Parks REIT|InvIT|Fund).*$/,'').replace(/\(.*\)/,'')})),{label:'Post-tax yield versus price to NAV',xl:'Post-tax distribution yield, %',yl:'Price / NAV',yRef:1,yRefL:'priced at NAV',xf:v=>v.toFixed(1)+'%',yf:v=>v.toFixed(2)})];
  return `<div class="grid g2" style="margin-bottom:14px"><section class="card"><h2>Yield vs price to NAV</h2><p class="hint">Right and low is best: high post-tax yield, bought below NAV. Colour = band.</p><div id="rsc"></div></section>
    <section class="card"><h2>Housing by city</h2><p class="hint">Valuation only; colour = band. Use the rent-vs-buy calculator on your own numbers.</p><div class="heat">${c.sort((a,b)=>a.score-b.score).map(i=>heatTile(i,`rent ${m(i,'Rent yield %')}%`)).join('')}</div></section></div>
  <section class="card"><h2>Listed REITs and InvITs</h2>${sortTable('re',[C.name,C.m('Type'),C.score,{k:'y',l:'Yield %',num:1,get:i=>m(i,'Distribution yield %'),fmt:i=>m(i,'Distribution yield %')??'—'},{k:'pty',l:'Post-tax %',num:1,get:i=>m(i,'Post-tax yield %'),fmt:i=>m(i,'Post-tax yield %')??'—'},{k:'sp',l:'Spread vs G-sec',num:1,get:i=>m(i,'Spread vs G-sec (pp)'),fmt:i=>m(i,'Spread vs G-sec (pp)')??'—'},{k:'pn',l:'P/NAV',num:1,get:i=>m(i,'Price/NAV'),fmt:i=>m(i,'Price/NAV')??'—'},C.dd],r,{k:'score',dir:1,keep:['name','score','pty']})}</section>`}
const OVERVIEW={snapshot:ovSnapshot,india:ovIndia,global:ovGlobal,commod:ovCommod,crypto:ovCrypto,fixed:ovFixed,realestate:ovRE};

/* ---------- scoped tools ---------- */
function viewChanges(t){if(t==='snapshot')return viewMonth();
  const l=items,withHist=l.filter(i=>i.history&&i.history.length>1),buy=l.filter(i=>i.score<=35&&!notInvestable(i)).sort((a,b)=>a.score-b.score),trim=l.filter(i=>i.score>65).sort((a,b)=>b.score-a.score);
  return `${withHist.length?`<section class="card" style="margin-bottom:14px"><h2>Band changes since last month</h2><div class="chg">${withHist.map(i=>{const p=prevScore(i),pb=bandOf(p)[0],nb=bandOf(i.score)[0],d=(i.score-p).toFixed(1);return `<div class="chgc" data-id="${i.id}" role="button" tabindex="0"><div class="n">${esc(i.name)}</div><div style="margin:4px 0">${spark(i.history.slice(-12),150,40)}</div><div class="t">${p} → <b style="color:var(--ink)">${i.score}</b> (${d>0?'+':''}${d})</div><div class="t">${pb===nb?`Still ${nb}`:`<span class="moved">${pb} → ${nb}</span>`}</div></div>`}).join('')}</div></section>`:`<div class="empty" style="margin-bottom:14px">Readings in this tab have one month of history so far; band changes appear after the next monthly run (3rd).</div>`}
  <div class="grid g2"><section class="card"><h2>In the Buy zone (35 or lower)</h2>${buy.map(i=>rowHTML(i,`<span class="tag">${esc(shortAct(i))}</span>`)).join('')||'<div class="empty">None this month.</div>'}</section>
  <section class="card"><h2>In the Trim zone (above 65)</h2>${trim.map(i=>rowHTML(i,`<span class="tag">${esc(shortAct(i))}</span>`)).join('')||'<div class="empty">None this month.</div>'}</section></div>`}
function viewKnowTab(t){const rel=TABS[t].notes;
  return `<section class="card"><h2>Notes related to ${TABS[t].t}</h2><p class="hint">From the knowledge base. Opens in the full library.</p><div id="knowl" class="klinks">${rel.length?'Loading…':'<div class="empty">No notes for this asset class yet. Send a video or article on it and it will be added here.</div>'}</div><p style="margin-top:10px"><a href="#knowledge">Open the full knowledge library →</a></p></section>`}
async function drawKnowTab(t){const el=document.getElementById('knowl');if(!el||!TABS[t].notes.length)return;
  try{if(!KNOW){const r=await fetch('knowledge/index.json?t='+Date.now(),{cache:'no-store'});KNOW=((await r.json()).notes||[]).sort((a,b)=>(!!b.pinned-!!a.pinned)||(b.added||'').localeCompare(a.added||''))}
    el.innerHTML=TABS[t].notes.map(s=>KNOW.find(n=>n.slug===s)).filter(Boolean).map(n=>`<a class="kitem" href="#knowledge/${encodeURIComponent(n.slug)}"><span class="kt">${esc(n.title)}</span><span class="km">${esc(n.source||'')} · ${esc(n.added||'')}</span></a>`).join('')}
  catch(e){el.innerHTML='<div class="empty">Could not load the notes.</div>'}}
function viewHealth(){return `<div class="card"><h2>Data health</h2><p class="hint">Live prices against the prices each model was scored at, and how fresh each model's inputs are.</p></div>${healthHTML()}`}

/* ---------- per-item tools in the side panel ---------- */
const _openDrawer=openDrawer;
openDrawer=function(id){_openDrawer(id);const i=byId[id];if(!i)return;const t=tabOf(i);
  const tools=[];
  if(i.history&&i.history.length>1)tools.unshift([`#${t}/trends`,'Trend',()=>{SERIES_ALL.forEach(([k])=>trendState.on[k]=k===i.id?1:0)}]);
  if(!tools.length)return;
  const bar=document.createElement('div');bar.className='dtools';bar.innerHTML=`<span class="tag">Open in ${TABS[t].t}:</span>`+tools.map((x,k)=>`<a class="btn" href="${x[0]}" data-k="${k}">${x[1]}</a>`).join('');
  bar.querySelectorAll('a').forEach(a=>a.onclick=()=>{const f=tools[+a.dataset.k][2];if(f)f();closeDrawer()});
  const h=dr.querySelector('.dtabs')||dr.querySelector('#drh');h.insertAdjacentElement('beforebegin',bar)};

/* ---------- router ---------- */
const LEGACY={month:'snapshot/changes',signals:'snapshot/finder',map:'snapshot/map',classes:'snapshot',trends:'snapshot/trends',alerts:'snapshot/alerts'};
const TOOLVIEW={finder:[viewSignals,drawSignals],map:[viewMap,bindMap],trends:[viewTrends,bindTrends],alerts:[viewAlerts,null],changes:[null,null],know:[null,null]};
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
  const hd=items.filter(i=>!i.wide),wd=items.length-hd.length;
  const bar=`<div class="tabhead"><div><h1 class="tabt">${TABS[t].t}</h1><p class="tabs">${TABS[t].sub}</p></div><div class="tabmix">${bandMix(hd,8)}<span class="tag">${hd.length} headline reading${hd.length>1?'s':''}${wd?` · +${wd} more watchlist stocks`:''}</span></div></div>
    <div class="tbar" aria-label="Views for ${TABS[t].t}">${TOOLS.filter(([k])=>!k||toolOK(t,k)).map(([k,l])=>`<a class="${k===tool?'on':''}" href="#${t}${k?'/'+k:''}" aria-current="${k===tool?'page':'false'}">${l}</a>`).join('')}</div>
    ${!tool?verdictLine(t):''}`;
  let body,after=null;
  if(!tool){body=OVERVIEW[t]();after=()=>{OV_DRAW.forEach(f=>f());if(t==='india')drawSX()}}
  else if(tool==='changes')body=viewChanges(t);
  else if(tool==='know'){body=viewKnowTab(t);after=()=>drawKnowTab(t)}
  else{body=TOOLVIEW[tool][0]();after=TOOLVIEW[tool][1]}
  m.innerHTML=bar+`<div class="tabbody">${body}</div>`;bindRows(m);bindSort(m);
  m.querySelectorAll('.vlink').forEach(x=>x.onclick=e=>{e.preventDefault();openDrawer(x.dataset.id)});
  m.querySelectorAll('.at[href]').forEach(x=>x.onclick=null);
  if(after)after();
  if(t==='india'&&!tool){
    m.querySelectorAll('.heatseg button').forEach(x=>{x.onclick=()=>{indState.heat=x.dataset.v;rerender()}});
    m.querySelectorAll('#stseg button').forEach(x=>{x.classList.toggle('on',x.dataset.v===indState.stockView);x.onclick=()=>{indState.stockView=x.dataset.v;rerender()}});
    m.querySelectorAll('#uniseg button').forEach(x=>{x.classList.toggle('on',x.dataset.v===indState.uni);x.onclick=()=>{indState.uni=x.dataset.v;indState.sec='all';rerender()}});
    const ss=m.querySelector('#secsel');if(ss)ss.onchange=()=>{indState.sec=ss.value;rerender()};
    m.querySelectorAll('.vsw button').forEach(x=>x.onclick=()=>{indState.view=x.dataset.v;try{localStorage.setItem('eeb-india-view',x.dataset.v)}catch(e){}rerender()});
    m.querySelectorAll('#valseg button').forEach(x=>{x.classList.toggle('on',+x.dataset.v===indState.valMax);x.onclick=()=>{indState.valMax=+x.dataset.v;rerender()}});
    m.querySelectorAll('.hmc,.hmcell').forEach(x=>x.onclick=()=>{const c=[x.dataset.s||null,x.dataset.k||null];indState.cell=c[0]||c[1]?c:null;rerender()});
    const hc_=m.querySelector('#hmclear');if(hc_)hc_.onclick=()=>{indState.cell=null;rerender()};
    const dva=m.querySelector('#dvall');if(dva)dva.onchange=()=>{indState.dvAll=dva.checked;rerender()};
  }
}
addEventListener('hashchange',()=>{route();window.scrollTo(0,0)});
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>{if(!CUR.tool&&TABS[CUR.tab]){OV_DRAW.forEach(f=>f());if(CUR.tab==='india')drawSX()}else if(CUR.tool==='map')drawMap();else if(CUR.tool==='trends')drawTrends();else if(CUR.tool==='finder')drawSignals()},150)});
freshLine();route();fetchLive();
