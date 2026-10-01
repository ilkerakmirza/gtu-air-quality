# GTÜ Hava Kalitesi — Claude çalışma kuralları

Bu proje hem Claude masaüstü uygulamasında hem de Claude Code web (bulut) oturumlarında geliştiriliyor.
Tek bir güncel sürüm olması için **tek kaynak `main` branch'idir**.

## Her oturumun başında
1. `git fetch origin main`
2. `main`'e geç ve güncelle: `git checkout main && git pull origin main`
   (Yerelde commit'lenmemiş değişiklik varsa önce kullanıcıya sor.)

## İş bitince
1. Değişiklikleri açıklayıcı bir mesajla commit'le.
2. Push'tan hemen önce tekrar `git pull origin main` (diğer ortamda yapılan iş varsa birleştir).
3. `git push origin main`
4. Bulut oturumunda ayrı bir çalışma branch'i kullanılıyorsa, o branch'i de `main` ile aynı commit'e getir ve push et.

Değişiklikler `main`'e geldiğinde GitHub Pages sitesi de güncellenir:
https://ilkerakmirza.github.io/gtu-air-quality/frontend_v2/

## Proje yapısı
- `frontend_v2/` — yayındaki arayüz (`index.html`, `js/app.js`, `js/api.js`, `js/campus.js`, `js/colorscale.js`, `data/campus.geojson`)
- `frontend/` — önceki harita arayüzü (`map.html`)
- `backend/` — Python sunucu ve veri toplayıcılar (PurpleAir, Atmotube, Tuya CO2, ÇSB, İBB); Railway ile çalışır (`Procfile`, `railway.json`)
- Yerelde önizleme: `python -m http.server 8765 --directory frontend_v2` → http://localhost:8765
