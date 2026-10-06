"""Telifsiz fon müziği üretici (tamamen sentezlenir): python music.py <süre_sn> <çıktı.wav> [tempo]
Sakin, akademik tonda: La minör – Fa – Do – Sol döngüsü; pad + yumuşak arpej + bas + hafif ritim."""
import sys, wave, numpy as np
D = float(sys.argv[1]); OUT = sys.argv[2]; BPM = float(sys.argv[3]) if len(sys.argv) > 3 else 88
SR = 44100; N = int(D * SR); t = np.arange(N) / SR
beat = 60 / BPM; bar = 4 * beat
L = np.zeros(N); R = np.zeros(N)
f = lambda m: 440 * 2 ** ((m - 69) / 12)
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ARP = [0, 1, 2, 1, 2, 3, 2, 1]
rng = np.random.default_rng(4)

def add(sig, start, gl, gr):
    i = int(start * SR); j = min(N, i + len(sig))
    if i >= N: return
    L[i:j] += sig[:j - i] * gl; R[i:j] += sig[:j - i] * gr

nbars = int(np.ceil(D / bar)) + 1
for b in range(nbars):
    ch = CH[(b // 2) % 4] if False else CH[b % 4]
    st = b * bar
    # pad: 2 akor tonu + oktav, yumuşak giriş/çıkış
    n = int((bar + 1.2) * SR); tt = np.arange(n) / SR
    env = np.minimum(1, tt / 0.9) * np.minimum(1, np.maximum(0, (bar + 1.2 - tt) / 1.2))
    pad = sum(np.sin(2 * np.pi * f(m) * tt + k) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.21 * tt + k)) + 0.35 * np.sin(2 * np.pi * f(m) * 1.003 * tt)
              for k, m in enumerate(ch))
    add(pad * env * 0.055, st, 0.9, 1.0)
    # bas
    nb = int(bar * SR); tb = np.arange(nb) / SR
    bass = np.sin(2 * np.pi * f(ch[0] - 12) * tb) * np.exp(-tb * 0.9) * np.minimum(1, tb / 0.02)
    add(bass * 0.16, st, 1, 1)
    # arpej (4. ölçüden sonra)
    if st >= 2 * bar:
        tones = ch + [ch[0] + 12]
        for k in range(8):
            m = tones[ARP[k]] + 12; na = int(1.2 * SR); ta = np.arange(na) / SR
            pl = (np.sin(2 * np.pi * f(m) * ta) + 0.25 * np.sin(4 * np.pi * f(m) * ta)) * np.exp(-ta * 4.2) * np.minimum(1, ta / 0.004)
            pan = 0.35 + 0.3 * (k % 2)
            add(pl * 0.06, st + k * beat / 2, 1 - pan + 0.35, pan + 0.35)
    # ritim (6. ölçüden sonra): yumuşak vuruş + ofbit tıkırtı
    if st >= 4 * bar:
        for k in range(4):
            if k % 2 == 0:
                nk = int(0.35 * SR); tk = np.arange(nk) / SR
                kick = np.sin(2 * np.pi * (48 + 60 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 9)
                add(kick * 0.22, st + k * beat, 1, 1)
            nh = int(0.06 * SR); hat = rng.standard_normal(nh) * np.exp(-np.arange(nh) / SR * 70)
            hat = np.diff(hat, prepend=0)
            add(hat * 0.018, st + k * beat + beat / 2, 0.8, 1)

# basit yankı (çok dokunuşlu gecikme)
for d, g in [(0.113, 0.28), (0.197, 0.22), (0.293, 0.17), (0.41, 0.12)]:
    k = int(d * SR)
    L[k:] += R[:-k] * g; R[k:] += L[:-k] * g * 0.9
fade = np.minimum(1, t / 1.5) * np.minimum(1, np.maximum(0, (D - t) / 3.0))
L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max()); L, R = L / peak * 0.7, R / peak * 0.7
data = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print("müzik:", OUT, D, "sn")
