# Deploy: Railway (backend) + Vercel (Meja Pimpinan)

Panduan ini memasang AmanCair secara online:

```
Browser ──► Vercel (Next.js, Meja Pimpinan)
               │  rewrites /api/* (server-side, cookie tetap di domain Vercel)
               ▼
            Railway (FastAPI + MCP + SQLite di volume /data)
               ▲
WorkBuddy ─────┘  konektor MCP: https://<domain-railway>/mcp/
```

Urutannya penting: **Railway dulu**, karena Vercel butuh URL backend saat build.

## Yang disiapkan di repo

| Berkas | Fungsi |
|---|---|
| `Dockerfile` (root) | Image backend. Konteks build root repo supaya draf contoh `workbuddy-spj/keluar/draf/` ikut masuk |
| `railway.json` | Builder Dockerfile, healthcheck `/docs`, 1 replika |
| `.dockerignore` | Membuang `frontend/`, `node_modules`, `.venv`, data lokal |
| `backend/seed/spj_demo.json` | Empat SPJ contoh (001, 002, 008, 010) yang otomatis diajukan saat backend menyala, supaya Meja Pimpinan tidak kosong |

Nilai bawaan di image: `DATA_DIR=/data`, `SPJ_DRAF_ROOT=/app/demo-draf`, `SPJ_SIAP_ROOT=/data/siap-cair`, `SPJ_SEED_FILE=/app/seed/spj_demo.json`.

## 1. Railway: backend

### Lewat dashboard

1. Buka https://railway.com/new, pilih **Deploy from GitHub repo**, pilih `zgii14/amancair`. Izinkan Railway mengakses repo bila diminta.
2. Biarkan **Root Directory** kosong (root repo). Railway membaca `railway.json` dan membangun dari `Dockerfile`.
3. Buka service, tab **Variables**, tambahkan:

   | Variabel | Nilai |
   |---|---|
   | `DEMO_PASSWORD` | sandi login Meja Pimpinan, misalnya `amancair-demo-2026` |
   | `MCP_TOKENS` | `<token-acak>=diskominfo:tim_spj` |

   Buat token acak dengan `openssl rand -hex 24` atau `python -c "import secrets;print(secrets.token_hex(24))"`. Jangan pakai `tok-spj` dari contoh lokal.

4. Klik kanan canvas proyek (atau tombol **+ New**), pilih **Volume**, sambungkan ke service backend dengan **Mount path** `/data`. Tanpa volume, database dan folder siap-cair hilang setiap redeploy (SPJ contoh akan diajukan ulang, tetapi riwayat persetujuan hilang).
5. Tab **Settings** > **Networking** > **Generate Domain**. Railway akan memberi domain seperti `amancair-production.up.railway.app`. Port diambil otomatis dari `$PORT`.
6. Tunggu deploy hijau, lalu cek:

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://<domain-railway>/docs
   ```

   Hasilnya harus `200`. Log deploy juga menampilkan `StreamableHTTP session manager started`.

### Atau lewat CLI

```bash
railway login
railway init --name amancair
railway up
railway variable set "DEMO_PASSWORD=amancair-demo-2026" "MCP_TOKENS=<token-acak>=diskominfo:tim_spj"
railway volume add --mount-path /data
railway domain
```

Jalankan dari root repo. `railway up` mengunggah kode lokal; deploy dari GitHub (cara dashboard) lebih enak karena setiap push ke `main` otomatis redeploy.

### Catatan backend

- `RAILWAY_PUBLIC_DOMAIN` diisi Railway otomatis dan dipakai backend untuk mengizinkan Host tersebut di endpoint MCP. FastMCP menolak Host selain localhost (HTTP 421) kalau tidak didaftarkan. Untuk custom domain, tambahkan `MCP_ALLOWED_HOSTS=api.domainmu.com`.
- Sesi login disimpan di memori proses. Setelah redeploy atau restart, pengguna perlu login ulang. Karena itu `numReplicas` dipatok 1.
- `FRONTEND_ORIGIN` tidak perlu diisi, karena browser tidak memanggil Railway langsung; semua lewat proxy Vercel.

## 2. Vercel: Meja Pimpinan

1. Buka https://vercel.com/new, impor `zgii14/amancair`.
2. **Root Directory**: klik Edit, pilih `frontend`. Framework terdeteksi sebagai Next.js; build command dan output biarkan bawaan.
3. **Environment Variables**:

   | Variabel | Nilai |
   |---|---|
   | `BACKEND_URL` | `https://<domain-railway>` (tanpa garis miring di akhir) |

4. Klik **Deploy**.

`BACKEND_URL` dibaca saat build (di `next.config.ts`). Kalau nanti domain Railway berubah, ubah variabelnya lalu **Redeploy** di Vercel; mengubah variabel saja tidak cukup.

CLI (opsional):

```bash
npm i -g vercel
cd frontend
vercel link
vercel env add BACKEND_URL production
vercel --prod
```

## 3. Uji ujung ke ujung

1. Buka `https://<domain-vercel>/login`.
2. Pilih profil **Diskominfo Kab. Sejahtera**, ID `sri`, sandi = `DEMO_PASSWORD`.
3. Halaman `/spj` menampilkan empat SPJ contoh:

   | SPJ | Risiko | Yang bisa ditunjukkan |
   |---|---|---|
   | SPJ-2026-001 | normal | Setujui langsung; status jadi DICAIRKAN |
   | SPJ-2026-002 | normal | Struk taksi ganda dihitung sekali |
   | SPJ-2026-008 | tinggi | Boarding pass atas nama orang lain; tombol butuh centang konfirmasi |
   | SPJ-2026-010 | tinggi | Total di atas Rp10 juta |

4. Buka salah satu berkas dari lembar SPJ (misalnya `rekap.xlsx`) untuk memastikan unduhan lewat proxy berjalan.
5. Setujui SPJ-2026-001, lalu buka `/audit`: harus ada baris `spj_diajukan` dan `spj_dicairkan`, dan rantai hash berstatus utuh.
6. Coba login sebagai `tim_spj` (akun agen): SPJ tidak bisa dibuka apalagi disetujui.

## 4. Sambungkan WorkBuddy ke backend online

Di WorkBuddy, tambahkan konektor MCP kustom:

- URL: `https://<domain-railway>/mcp/` (dengan garis miring di akhir)
- Header: `Authorization: Bearer <token-acak>`

Tes cepat dari terminal:

```bash
curl -s https://<domain-railway>/mcp/ \
  -H "Authorization: Bearer <token-acak>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Daftar tool harus memuat `ajukan_spj`.

**Batasan penting.** Backend menghitung sidik dari berkas yang ada di disknya sendiri (`/app/demo-draf`), bukan dari laptop tempat WorkBuddy berjalan. Jadi di versi online, `ajukan_spj` hanya berhasil untuk nomor SPJ yang drafnya sudah ikut di image. Untuk draf baru:

- **Demo langsung** (rekam video): jalankan backend lokal dengan `SPJ_DRAF_ROOT` menunjuk ke folder WorkBuddy, seperti di README utama.
- **Memperbarui versi online**: jalankan `python scripts/sinkron_workbuddy.py`, commit, push. Railway membangun ulang image dengan draf terbaru.

Mengunggah berkas draf lewat MCP belum dibuat; itu langkah berikutnya bila backend dipakai di luar demo.

## Masalah yang sering muncul

| Gejala | Penyebab | Perbaikan |
|---|---|---|
| Deploy Railway gagal `DEMO_PASSWORD wajib diisi` | Variabel belum diisi | Isi di tab Variables, redeploy |
| `MCP_TOKENS merujuk user tidak dikenal` | Salah tulis profil atau user | Format harus `token=diskominfo:tim_spj` |
| Login di Vercel selalu gagal / 500 | `BACKEND_URL` salah atau belum redeploy setelah diubah | Buka `https://<domain-vercel>/api/profil`: harus membalas 401 `{"detail":"Belum login"}` dari backend. Kalau 404/500, perbaiki variabel lalu redeploy |
| MCP membalas 421 Misdirected Request | Host tidak terdaftar (custom domain) | Tambahkan `MCP_ALLOWED_HOSTS` |
| MCP membalas 401 | Header token salah | Pastikan `Bearer ` diikuti token yang sama dengan `MCP_TOKENS` |
| SPJ hilang setelah redeploy | Volume belum dipasang di `/data` | Tambah volume, redeploy |
| `ajukan_spj` gagal "Folder draf ... tidak ditemukan" | Draf tidak ada di image | Lihat bagian Batasan di atas |
