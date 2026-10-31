# Meja Pimpinan (frontend)

Antarmuka web untuk pejabat yang memutuskan: bendahara meninjau SPJ yang diajukan tim agen, lalu menyetujui atau menolaknya. Dibuat dengan Next.js 15 (App Router) dan React 19, tanpa pustaka UI tambahan.

## Menjalankan

```bash
npm install
npm run dev
```

Buka http://localhost:3000. Backend harus berjalan di `http://127.0.0.1:8000`, atau atur alamatnya lewat variabel `BACKEND_URL`. Semua panggilan `/api/*` diteruskan ke backend melalui rewrites di `next.config.ts`, sehingga cookie sesi tetap satu origin.

## Halaman

| Rute | Isi |
|---|---|
| `/login` | Masuk dengan profil organisasi dan ID pegawai |
| `/spj` | Daftar SPJ yang menunggu keputusan dan yang sudah diputuskan |
| `/spj/[nomor]` | Lembar SPJ: total, temuan per level risiko, perintah tersisip, berkas dari agen, tombol Setujui/Tolak |
| `/audit` | Jejak audit dan status rantai hash |
| `/`, `/rencana/[id]`, `/riwayat` | Halaman prototipe disposisi surat (profil perusahaan dan kecamatan) |

## Pemeriksaan

```bash
npm run lint
npx tsc --noEmit
npm run build
```
