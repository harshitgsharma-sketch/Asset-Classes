/* Entry/Exit Board service worker: network first, so the board is always current when online;
   the last good copy of the page, script and data is served when offline. Same-origin GETs only. */
const CACHE='eeb-v1';
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['./','index.html','app.js','data/signals.json','icon.svg','manifest.webmanifest']).catch(()=>{})))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const r=e.request,u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  e.respondWith(fetch(r).then(res=>{
    if(res.ok){const copy=res.clone();const key=u.origin+u.pathname;caches.open(CACHE).then(c=>c.put(key,copy))}
    return res}).catch(()=>caches.match(u.origin+u.pathname).then(m=>m||caches.match(r,{ignoreSearch:true}))))});
