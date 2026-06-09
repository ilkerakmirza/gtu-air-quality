// Timeline slider — drives date-range filtering on the map
// Depends on: noUiSlider (loaded from CDN in map.html)

const Timeline = (() => {
    let _slider = null;
    let _onChange = null;

    // Preset buttons config
    const PRESETS = [
        { label: "Son 24 saat", days: 1 },
        { label: "Son 7 gün",   days: 7 },
        { label: "Son 30 gün",  days: 30 },
        { label: "Tüm veriler", days: null },
    ];

    function _isoOf(date) {
        return date.toISOString();
    }

    function _daysAgo(n) {
        const d = new Date();
        d.setDate(d.getDate() - n);
        return d;
    }

    function init(sliderId, presetContainerId, onChange) {
        _onChange = onChange;
        const sliderEl = document.getElementById(sliderId);
        const presetsEl = document.getElementById(presetContainerId);

        if (!sliderEl || typeof noUiSlider === "undefined") {
            console.warn("[timeline] noUiSlider not available or slider element missing");
            return;
        }

        const now   = new Date();
        const start = _daysAgo(30);

        noUiSlider.create(sliderEl, {
            start: [start.getTime(), now.getTime()],
            connect: true,
            range: { min: _daysAgo(365).getTime(), max: now.getTime() },
            step: 60 * 60 * 1000, // 1 hour steps
        });

        _slider = sliderEl.noUiSlider;

        _slider.on("change", (values) => {
            _fireChange(values);
        });

        // Build preset buttons
        PRESETS.forEach(p => {
            const btn = document.createElement("button");
            btn.className = "timeline-preset-btn";
            btn.textContent = p.label;
            btn.addEventListener("click", () => {
                const endDate = new Date();
                const startDate = p.days ? _daysAgo(p.days) : _daysAgo(365);
                _slider.set([startDate.getTime(), endDate.getTime()]);
                _fireChange([startDate.getTime(), endDate.getTime()]);
                document.querySelectorAll(".timeline-preset-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
            presetsEl.appendChild(btn);
        });

        // Activate "Son 30 gün" by default
        presetsEl.children[2]?.classList.add("active");
    }

    function _fireChange(values) {
        const [s, e] = values.map(v => new Date(Number(v)));
        const label = document.getElementById("timeline-label");
        if (label) {
            label.textContent = `${_fmt(s)} — ${_fmt(e)}`;
        }
        if (_onChange) _onChange(_isoOf(s), _isoOf(e));
    }

    function _fmt(date) {
        return date.toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
    }

    function getRange() {
        if (!_slider) return { start: null, end: null };
        const [s, e] = _slider.get().map(v => new Date(Number(v)));
        return { start: _isoOf(s), end: _isoOf(e) };
    }

    return { init, getRange };
})();
