// Gün animasyon oynatıcısı
// Ayşe'nin günü boyunca izlediği rotayı adım adım oynatır.
// Bağımlılıklar: Leaflet, colorscale.js, api.js

const Player = (() => {
    let _points      = [];   // [{lat, lon, pm2_5, recorded_at, activity}, ...]
    let _idx         = 0;
    let _timer       = null;
    let _speed       = 4;    // adım/saniye
    let _trailLayer  = null;
    let _dotMarker   = null;
    let _map         = null;
    let _onStep      = null; // callback(point, idx, total)

    // ── Dışa açık API ─────────────────────────────────────────────────────────

    function init(map, onStep) {
        _map     = map;
        _onStep  = onStep;
        _trailLayer = L.layerGroup().addTo(map);
    }

    async function loadSession(sessionId) {
        const res = await API.sessionReadings(sessionId);
        // Sadece GPS'li ve PM2.5 olan noktalar, zamana göre sırala
        _points = res.data
            .filter(r => r.lat && r.lon && r.pm2_5 != null)
            .sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));
        return _points.length;
    }

    function play() {
        if (!_points.length) return;
        if (_timer) return; // zaten oynuyor
        _timer = setInterval(_step, 1000 / _speed);
    }

    function pause() {
        clearInterval(_timer);
        _timer = null;
    }

    function stop() {
        pause();
        _idx = 0;
        _trailLayer.clearLayers();
        if (_dotMarker) { _map.removeLayer(_dotMarker); _dotMarker = null; }
    }

    function setSpeed(s) { _speed = s; if (_timer) { pause(); play(); } }

    function isPlaying() { return _timer !== null; }

    function progress() { return _points.length ? _idx / _points.length : 0; }

    function seekTo(fraction) {
        _idx = Math.min(Math.floor(fraction * _points.length), _points.length - 1);
        _render(_points[_idx]);
    }

    // Yüklü oturumun zaman aralığını döner (PurpleAir senkronizasyonu için)
    function getTimeRange() {
        if (!_points.length) return { start: null, end: null };
        return {
            start: _points[0].recorded_at,
            end:   _points[_points.length - 1].recorded_at,
        };
    }

    // ── İç fonksiyonlar ───────────────────────────────────────────────────────

    function _step() {
        if (_idx >= _points.length) { pause(); return; }
        const pt = _points[_idx];
        _render(pt);
        if (_onStep) _onStep(pt, _idx, _points.length);
        _idx++;
    }

    function _render(pt) {
        const color = pm25Color(pt.pm2_5);

        // Geçmiş noktayı kalıcı dot olarak bırak
        if (_idx > 0) {
            const prev = _points[_idx - 1];
            if (prev.lat && prev.lon) {
                const prevColor = pm25Color(prev.pm2_5);
                L.circleMarker([prev.lat, prev.lon], {
                    radius: 6, color: prevColor, weight: 1,
                    fillColor: prevColor, fillOpacity: 0.85,
                }).addTo(_trailLayer);
            }
        }

        // Hareketli nokta (büyük, parlak)
        const icon = L.divIcon({
            className: "",
            html: `<div class="player-dot" style="background:${color};box-shadow:0 0 0 4px ${color}55,0 0 12px ${color}88"></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        });

        if (!_dotMarker) {
            _dotMarker = L.marker([pt.lat, pt.lon], { icon, zIndexOffset: 1000 }).addTo(_map);
        } else {
            _dotMarker.setLatLng([pt.lat, pt.lon]);
            _dotMarker.setIcon(icon);
        }
    }

    return { init, loadSession, play, pause, stop, setSpeed, isPlaying, progress, seekTo, getTimeRange };
})();
