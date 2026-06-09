import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add nav link (before Araştırma)
html = html.replace(
    '<a href="#research">Araştırma</a>',
    '<a href="#research">Araştırma</a>\n      <a href="#sensors">Sensörler</a>'
)

# 2. CSS for sensors section — insert before /* ===== MONITORING ===== */
sensor_css = """
/* ===== SENSORS ===== */
#sensors{background:var(--white);}
.sensors-intro{text-align:center;max-width:760px;margin:0 auto 48px;font-size:.93rem;color:var(--text-muted);line-height:1.75;}
.sensors-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;}
.sensor-type-badge{
  display:inline-flex;align-items:center;gap:6px;
  font-size:.65rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  padding:5px 12px;border-radius:20px;margin-bottom:14px;
}
.badge-fixed{background:rgba(124,58,237,.1);color:#7c3aed;border:1px solid rgba(124,58,237,.25);}
.badge-portable{background:rgba(0,180,216,.1);color:#0891b2;border:1px solid rgba(0,180,216,.25);}
.sensor-product-card{
  background:var(--white);border-radius:18px;
  border:1px solid var(--border);box-shadow:var(--card-shadow);
  overflow:hidden;transition:transform .3s,box-shadow .3s;
  display:flex;flex-direction:column;
}
.sensor-product-card:hover{transform:translateY(-6px);box-shadow:0 16px 40px rgba(26,79,138,.15);}
.sensor-product-card.fixed-station{border-top:5px solid #7c3aed;}
.sensor-product-card.portable-sensor{border-top:5px solid #0891b2;}
.sensor-img-wrap{
  height:220px;background:var(--bg2);
  display:flex;align-items:center;justify-content:center;
  padding:24px;position:relative;overflow:hidden;
}
.sensor-img-wrap::after{
  content:'';position:absolute;inset:0;
  background:radial-gradient(circle at center,rgba(255,255,255,.4),transparent 70%);
}
.sensor-img-wrap img{
  max-width:100%;max-height:180px;
  object-fit:contain;position:relative;z-index:1;
  filter:drop-shadow(0 4px 12px rgba(0,0,0,.15));
  transition:transform .3s;
}
.sensor-product-card:hover .sensor-img-wrap img{transform:scale(1.06);}
.sensor-card-body{padding:22px 24px;flex:1;display:flex;flex-direction:column;gap:12px;}
.sensor-card-name{font-size:1.1rem;font-weight:800;color:var(--dark);}
.sensor-card-role{font-size:.78rem;color:var(--text-muted);line-height:1.55;}
.sensor-params{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;}
.sensor-param{
  font-size:.65rem;font-weight:600;padding:3px 9px;border-radius:12px;
  background:var(--bg2);color:var(--text);border:1px solid var(--border);
}
.sensor-param.highlight{background:rgba(26,79,138,.08);color:var(--primary);border-color:rgba(26,79,138,.18);}
.sensor-specs-table{margin-top:4px;border-radius:8px;overflow:hidden;border:1px solid var(--border);}
.sensor-spec-row{
  display:grid;grid-template-columns:1fr 1.2fr;
  font-size:.73rem;border-bottom:1px solid var(--border);
}
.sensor-spec-row:last-child{border-bottom:none;}
.spec-key{padding:7px 10px;background:var(--bg);color:var(--text-muted);font-weight:600;}
.spec-val{padding:7px 10px;color:var(--text);}
.sensor-card-link{
  display:flex;align-items:center;justify-content:center;gap:7px;
  margin-top:auto;padding:10px 16px;border-radius:8px;
  font-size:.78rem;font-weight:600;text-decoration:none;
  background:rgba(26,79,138,.06);border:1px solid rgba(26,79,138,.15);
  color:var(--primary-light);transition:background .2s;
}
.sensor-card-link:hover{background:rgba(26,79,138,.12);}
@media(max-width:900px){.sensors-grid{grid-template-columns:1fr 1fr;}}
@media(max-width:600px){.sensors-grid{grid-template-columns:1fr;}}
"""

html = html.replace('/* ===== MONITORING ===== */', sensor_css + '\n/* ===== MONITORING ===== */')

# 3. HTML section — insert after #research section, before #projects
sensors_html = """
<!-- ===== SENSORS ===== -->
<section id="sensors">
  <div class="section-inner">
    <div class="section-header fade-in">
      <div class="section-tag">Kullanılan Sensörler</div>
      <h2 class="section-title">Ölçüm <span>Platformları</span></h2>
      <p class="section-desc">Araştırmamızda iki farklı yaklaşım kullanılmaktadır: kampüse entegre sabit sensör ağı ile arka plan değerlerinin izlenmesi ve taşınabilir sensörler ile bireylerin aktüel maruziyetinin belirlenmesi.</p>
      <div class="divider"></div>
    </div>

    <div class="sensors-intro fade-in">
      <p><strong>Hibrit sensör yaklaşımı:</strong> Sabit dış ortam istasyonu (PurpleAir) sürekli arka plan PM₂.₅ verisini sağlarken, taşınabilir sensörler (Atmotube PRO ve Novato) bireylerin mikro-ortamlar arasındaki hareketini gerçek zamanlı olarak takip eder. İç/dış ortam oranı (I/O ratio) bu iki katman birleştirilerek hesaplanır.</p>
    </div>

    <div class="sensors-grid">

      <!-- PurpleAir PA-II -->
      <div class="sensor-product-card fixed-station fade-in">
        <div class="sensor-img-wrap" style="background:linear-gradient(135deg,#f3e8ff,#ede9fe);">
          <img src="https://www2.purpleair.com/cdn/shop/products/paii_side_9953_300x300.jpg"
               alt="PurpleAir PA-II"
               onerror="this.src='';this.parentElement.innerHTML='<div style=font-size:4rem;opacity:.4>📡</div>'">
        </div>
        <div class="sensor-card-body">
          <div>
            <span class="sensor-type-badge badge-fixed">🔵 Sabit İstasyon · Arka Plan İzleme</span>
            <div class="sensor-card-name">PurpleAir PA-II</div>
          </div>
          <div class="sensor-card-role">GTÜ kampüsüne entegre edilen sabit dış ortam istasyonu. İki bağımsız Plantower PMS5003 lazer partikül sayıcısı ile sürekli PM₂.₅ arka plan konsantrasyonu ölçer; veriler PurpleAir ağına ve kampüs izleme paneline gerçek zamanlı aktarılır.</div>
          <div>
            <div style="font-size:.68rem;color:var(--text-muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Ölçülen Parametreler</div>
            <div class="sensor-params">
              <span class="sensor-param highlight">PM₁.₀</span>
              <span class="sensor-param highlight">PM₂.₅</span>
              <span class="sensor-param highlight">PM₁₀</span>
              <span class="sensor-param">Sıcaklık</span>
              <span class="sensor-param">Nem</span>
            </div>
          </div>
          <div class="sensor-specs-table">
            <div class="sensor-spec-row"><span class="spec-key">Sensör Tipi</span><span class="spec-val">Plantower PMS5003 × 2</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Bağlantı</span><span class="spec-val">WiFi → PurpleAir Ağı</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Kurulum</span><span class="spec-val">Sabit dış ortam</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Veri</span><span class="spec-val">2 dk. ortalama, açık erişim</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Kampüs ID</span><span class="spec-val">#229263 – GTU</span></div>
          </div>
          <a href="https://map.purpleair.com/air-quality-raw-pm25?opt=%2F1%2Flp%2Fa0%2Fp604800%2FcC5&select=229263#6.19/39.93/29.94"
             target="_blank" class="sensor-card-link">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>
            Canlı Haritada Görüntüle
          </a>
        </div>
      </div>

      <!-- Atmotube PRO -->
      <div class="sensor-product-card portable-sensor fade-in">
        <div class="sensor-img-wrap" style="background:linear-gradient(135deg,#e0f2fe,#e0f7fa);">
          <img src="https://cdn.prod.website-files.com/5f23e100544c906cadf34322/6972134392681ace1bf8ffd8_product-img-1.jpg"
               alt="Atmotube PRO"
               onerror="this.src='';this.parentElement.innerHTML='<div style=font-size:4rem;opacity:.4>🌬️</div>'">
        </div>
        <div class="sensor-card-body">
          <div>
            <span class="sensor-type-badge badge-portable">🟢 Taşınabilir · Kişisel Maruziyet</span>
            <div class="sensor-card-name">Atmotube PRO</div>
          </div>
          <div class="sensor-card-role">Bireyin üzerinde taşınan giyilebilir hava kalitesi monitörü. Hareket halindeki kampüs kullanıcılarının farklı mikro-ortamlardaki anlık PM ve VOC maruziyetini GPS koordinatlarıyla birlikte kaydeder.</div>
          <div>
            <div style="font-size:.68rem;color:var(--text-muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Ölçülen Parametreler</div>
            <div class="sensor-params">
              <span class="sensor-param highlight">PM₁.₀</span>
              <span class="sensor-param highlight">PM₂.₅</span>
              <span class="sensor-param highlight">PM₁₀</span>
              <span class="sensor-param highlight">VOC</span>
              <span class="sensor-param">Sıcaklık</span>
              <span class="sensor-param">Nem</span>
              <span class="sensor-param">Basınç</span>
            </div>
          </div>
          <div class="sensor-specs-table">
            <div class="sensor-spec-row"><span class="spec-key">PM Sensörü</span><span class="spec-val">Sensirion SPS30</span></div>
            <div class="sensor-spec-row"><span class="spec-key">VOC Sensörü</span><span class="spec-val">Sensirion SGPC3</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Bağlantı</span><span class="spec-val">Bluetooth / USB-C</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Batarya</span><span class="spec-val">12 gün veri depolama</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Boyut / Ağırlık</span><span class="spec-val">86 × 50 × 22 mm · 106 g</span></div>
          </div>
          <a href="https://atmotube.com/atmotube-pro" target="_blank" class="sensor-card-link">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>
            Üretici Web Sitesi
          </a>
        </div>
      </div>

      <!-- Novato WiFi CO2 -->
      <div class="sensor-product-card portable-sensor fade-in">
        <div class="sensor-img-wrap" style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);">
          <img src="https://novato.com.tr/wp-content/uploads/2024/12/hava-kalitesi-sensoru-wifi.png"
               alt="Novato WiFi Hava Kalitesi Sensörü"
               onerror="this.src='';this.parentElement.innerHTML='<div style=font-size:4rem;opacity:.4>🔬</div>'">
        </div>
        <div class="sensor-card-body">
          <div>
            <span class="sensor-type-badge badge-portable">🟢 Taşınabilir · Kişisel Maruziyet</span>
            <div class="sensor-card-name">Novato WiFi CO₂ Sensörü</div>
          </div>
          <div class="sensor-card-role">NDIR teknolojisiyle yüksek hassasiyetli CO₂ ölçümü yapan WiFi bağlantılı sensör. Kapalı mikro-ortamlarda (derslik, kütüphane, kantin) havalandırma yeterliliği ve kullanıcı yoğunluğunun CO₂ göstergesi ile izlenmesinde kullanılır.</div>
          <div>
            <div style="font-size:.68rem;color:var(--text-muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Ölçülen Parametreler</div>
            <div class="sensor-params">
              <span class="sensor-param highlight">CO₂</span>
              <span class="sensor-param">Sıcaklık</span>
              <span class="sensor-param">Nem</span>
            </div>
          </div>
          <div class="sensor-specs-table">
            <div class="sensor-spec-row"><span class="spec-key">CO₂ Sensörü</span><span class="spec-val">NDIR (Non-Dispersive IR)</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Ölçüm Aralığı</span><span class="spec-val">400 – 9999 ppm (±50 ppm)</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Bağlantı</span><span class="spec-val">WiFi 2.4 GHz</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Güç</span><span class="spec-val">USB Type-C / DC 5V</span></div>
            <div class="sensor-spec-row"><span class="spec-key">Uygulama</span><span class="spec-val">Tuya / Smart Life</span></div>
          </div>
          <a href="https://novato.com.tr/urun/wifi-hava-kalitesi-sensoru/" target="_blank" class="sensor-card-link">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>
            Ürün Sayfası
          </a>
        </div>
      </div>

    </div><!-- end sensors-grid -->
  </div>
</section>

"""

# Insert after #research section, before #projects
html = html.replace('\n<!-- ===== PROJECTS ===== -->', sensors_html + '\n<!-- ===== PROJECTS ===== -->')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

size_mb = len(html.encode('utf-8')) / 1024 / 1024
print(f'Done. Size={size_mb:.1f}MB')
print('Sensors section added:', 'id="sensors"' in html)
print('Nav link added:', 'href="#sensors"' in html)
