
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# 1. Remove team-title divs (role text)
content = re.sub(r'\s*<div class="team-title">.*?</div>', '', content)

# 2. Replace live data function
old_start = '// ===== Air Quality Live Data (WAQI API) ====='
old_end   = 'setInterval(loadPurpleAir, 120000);'
s = content.find(old_start)
e = content.find(old_end) + len(old_end)

new_func = r"""// ===== PurpleAir Live Data – v1 API =====
// Get a free key: email contact@purpleair.com with your name
const PA_READ_KEY = '';   // <-- paste your PurpleAir READ key here

function aqiFromPm25(pm) {
  const bp=[[0,12,0,50],[12.1,35.4,51,100],[35.5,55.4,101,150],
    [55.5,150.4,151,200],[150.5,250.4,201,300],[250.5,350.4,301,400],[350.5,500.4,401,500]];
  for(const [clo,chi,ilo,ihi] of bp)
    if(pm>=clo&&pm<=chi) return Math.round(((ihi-ilo)/(chi-clo))*(pm-clo)+ilo);
  return Math.min(500, Math.max(0, Math.round(pm)));
}
function aqiClass(aqi){
  if(aqi<=50)  return['aqi-good','İyi'];
  if(aqi<=100) return['aqi-moderate','Orta'];
  if(aqi<=150) return['aqi-usg','Hassas Gruplar İçin Sağlıksız'];
  if(aqi<=200) return['aqi-unhealthy','Sağlıksız'];
  if(aqi<=300) return['aqi-very','Çok Sağlıksız'];
  return['aqi-haz','Tehlikeli'];
}
function setEl(id,val){ const e=document.getElementById(id); if(e) e.textContent=val; }

function showError(msg){
  const badge=document.getElementById('pa-live-badge');
  if(badge){ badge.textContent='Bağlantı Sorunu'; badge.style.cssText='background:rgba(248,113,113,.12);border-color:rgba(248,113,113,.3);color:#f87171;'; }
  const errEl=document.getElementById('pa-error');
  if(errEl){ errEl.innerHTML='<p>'+msg+'</p>'; errEl.style.display='block'; }
}

function loadPurpleAir(){
  document.getElementById('pa-live-badge').textContent='Yükleniyor…';
  document.getElementById('pa-error').style.display='none';

  if(!PA_READ_KEY){
    showError('PurpleAir API key girilmedi. <b>Nasıl alınır:</b> <a href="https://develop.purpleair.com/sign-in" target="_blank" style="color:#48cae4">develop.purpleair.com</a> adresinden ücretsiz kayıt olun, sonra <code style="background:rgba(255,255,255,.1);padding:1px 5px;border-radius:3px">PA_READ_KEY</code> değişkenine READ key\'i yapıştırın.');
    return;
  }

  const fields='pm2.5_atm,pm2.5_atm_a,pm2.5_atm_b,pm10.0_atm,pm1.0_atm,temperature,humidity,pressure,last_seen,name';
  const url='https://api.purpleair.com/v1/sensors/229263?fields='+fields;
  const ctrl=new AbortController();
  setTimeout(()=>ctrl.abort(),8000);

  fetch(url, {
    headers:{ 'X-API-Key': PA_READ_KEY },
    signal: ctrl.signal
  })
  .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
  .then(data=>{
    const s=data.sensor;
    if(!s) throw new Error('no sensor field');

    const pm25  = s['pm2.5_atm']   ?? 0;
    const pm25a = s['pm2.5_atm_a'] ?? pm25;
    const pm25b = s['pm2.5_atm_b'] ?? pm25;
    const pm10  = s['pm10.0_atm']  ?? 0;
    const pm1   = s['pm1.0_atm']   ?? 0;
    const tempF = s.temperature ?? 0;
    const tempC = ((tempF-32)*5/9).toFixed(1);
    const hum   = s.humidity ?? 0;
    const pres  = s.pressure ?? 0;
    const aqi   = aqiFromPm25(pm25);
    const [cls,label] = aqiClass(aqi);

    setEl('pa-pm25',   pm25.toFixed(1));
    setEl('pa-pm25-a', pm25a.toFixed(1));
    setEl('pa-pm25-b', pm25b.toFixed(1));
    setEl('pa-pm10',   pm10.toFixed(1));
    setEl('pa-pm1',    pm1.toFixed(1));
    setEl('pa-temp',   tempC);
    setEl('pa-hum',    hum.toFixed(0));
    setEl('pa-pressure', pres.toFixed(0));
    setEl('pa-aqi-val', aqi);
    setEl('pa-aqi-label', label);
    setEl('pa-name',   s.name||'GTÜ Kampüsü');

    const aqiEl=document.getElementById('pa-aqi-val');
    const lblEl=document.getElementById('pa-aqi-label');
    if(aqiEl) aqiEl.className='pa-card-value '+cls;
    if(lblEl) lblEl.className='pa-status-text '+cls;

    const needle=document.getElementById('pa-needle');
    if(needle) needle.style.left=Math.min(97,Math.max(3,(aqi/500)*100))+'%';

    const ts = s.last_seen ? new Date(s.last_seen*1000) : new Date();
    setEl('pa-updated', ts.toLocaleTimeString('tr-TR'));
    setEl('pa-last-seen', 'Sensör: '+(s.name||'GTÜ Kampüsü #229263')+' · '+ts.toLocaleString('tr-TR'));

    const badge=document.getElementById('pa-live-badge');
    if(badge){ badge.textContent='Canlı Veri – Sensör #229263'; badge.style.cssText='background:rgba(74,222,128,.12);border-color:rgba(74,222,128,.3);color:#4ade80;'; }
  })
  .catch(err=>{
    console.warn('PurpleAir error:',err);
    if(err.name==='AbortError') return showError('Bağlantı zaman aşımına uğradı.');
    showError('Veri alınamadı ('+err.message+'). API key ve bağlantıyı kontrol edin.');
  });
}

setTimeout(loadPurpleAir, 800);
setInterval(loadPurpleAir, 120000);"""

new_content = content[:s] + new_func + content[e:]
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done, length:', len(new_content))
print('team-title removed:', 'team-title' not in new_content)
