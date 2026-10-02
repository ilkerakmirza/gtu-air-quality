// Ekip görünümü kasası: saha ekibinin gerçek adlarını ekip koduyla şifreler (PBKDF2-SHA256 210000 → AES-GCM-256).
// Çıktıyı frontend_v2/js/app.js içindeki TEAM_VAULT değerine yapıştırın. Adlar kaynak koda düz metin olarak girmez (KVKK).
//
// Kullanım (Node 18+):
//   node scripts/ekip_kasasi.js "<ekip kodu>" '{"Ayse":["Ad","Baş harf"],"Ilker":["Ad","Baş harf"],"Serra":["Ad","Baş harf"]}'
// Anahtarlar, oturum adlarının başındaki önekle (app.js → PEOPLE[].key) aynı olmalı.
const { webcrypto: c } = require("crypto");
(async () => {
    const [code, json] = process.argv.slice(2);
    if (!code || !json) { console.error("Kullanım: node scripts/ekip_kasasi.js <kod> '<ad JSON>'"); process.exit(1); }
    const names = JSON.parse(json);
    const salt = c.getRandomValues(new Uint8Array(16)), iv = c.getRandomValues(new Uint8Array(12));
    const base = await c.subtle.importKey("raw", new TextEncoder().encode(code), "PBKDF2", false, ["deriveKey"]);
    const key = await c.subtle.deriveKey({ name: "PBKDF2", salt, iterations: 210000, hash: "SHA-256" },
        base, { name: "AES-GCM", length: 256 }, false, ["encrypt"]);
    const ct = new Uint8Array(await c.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(names))));
    const b64 = a => Buffer.from(a).toString("base64");
    console.log(JSON.stringify({ salt: b64(salt), iv: b64(iv), ct: b64(ct) }));
})();
