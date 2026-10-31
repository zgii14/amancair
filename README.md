# AmanCair — Sidik SPJ Perjalanan Dinas

> **SPJ diperiksa agen AI, cair setelah bendahara setuju.**
> AI agents check travel claims; money moves after approval.

Proyek untuk **AI CAN DO IT — Tencent Cloud Hackathon Indonesia 2026**, Challenge B (The Office Agent), skenario verifikasi kuitansi/faktur. Dibangun dengan **Tencent Cloud WorkBuddy**. Semua data fiktif.

AmanCair adalah tim tujuh agen di WorkBuddy yang memeriksa Surat Pertanggungjawaban (SPJ) perjalanan dinas dari bukti yang berantakan, mencocokkannya dengan SPT dan Standar Biaya Masukan, mengaudit ulang, lalu menyusun rekap dan draf SPJ. Agen hanya **menyiapkan**; bendahara **memutuskan** di Meja Pimpinan; backend yang **mencairkan** setelah memverifikasi bahwa berkas yang disetujui persis sama dengan yang diajukan.

## Dokumen pengumpulan
| Dokumen | File |
|---|---|
| Judul, blurb, deskripsi lengkap | [submission/01-judul-dan-deskripsi.md](submission/01-judul-dan-deskripsi.md) |
| Lembar akuntabilitas | [submission/02-lembar-akuntabilitas.md](submission/02-lembar-akuntabilitas.md) |
| Hasil uji | [submission/03-hasil-uji.md](submission/03-hasil-uji.md) |
| Diagram arsitektur | [submission/04-arsitektur.md](submission/04-arsitektur.md) |
| Product sharing (peran WorkBuddy & pelajaran) | [submission/05-product-sharing.md](submission/05-product-sharing.md) |
| Naskah video | [submission/06-naskah-video.md](submission/06-naskah-video.md) |

## Struktur repo
```
workbuddy-spj/            Proyek WorkBuddy (snapshot dari folder kerja agen)
  skills/                 SKILL.md untuk 7 agen
  export/spj-agent-team/  Export Expert Team WorkBuddy (lampiran wajib)
  data/                   Data fiktif: pegawai, SBM, SPT, libur, 11 kasus bukti
  aturan/bisnis.json      Aturan R01–R11
  keluar/                 Hasil agen: draf/ dan siap-cair/
  kerja/, log/            Hasil kerja per agen dan log audit berantai hash
  _bukti-workbuddy/       Memori proyek WorkBuddy (bukti pemakaian)
backend/                  Gerbang persetujuan: FastAPI + MCP + SQLite (pytest)
frontend/                 Meja Pimpinan (Next.js): halaman SPJ untuk bendahara
docs/workbuddy/           Prompt yang dipakai untuk membangun di WorkBuddy + panduan konektor
scripts/                  Utilitas (sinkron snapshot WorkBuddy ke repo)
```

## Arsitektur singkat
```
WorkBuddy Expert Team (Koordinator → 3 Pembaca paralel → Verifikator SBM → Auditor → Penyusun)
        │  tool MCP ajukan_spj (HTTP + bearer token)
        ▼
Backend: hitung sidik SHA-256 semua berkas draf ─► Meja Pimpinan: bendahara Setujui/Tolak
        │  sidik sama?  ya → salin byte-per-byte ke siap-cair (di luar folder agen) · tidak → ditolak
        ▼
Log audit berantai hash
```
Detail dan trade-off: [submission/04-arsitektur.md](submission/04-arsitektur.md).

## Menjalankan
**Backend**
```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest
DEMO_PASSWORD=demo123 MCP_TOKENS="tok-spj=diskominfo:tim_spj" SPJ_DRAF_ROOT="<folder>/spj-agent/keluar/draf" .venv/Scripts/python -m uvicorn app.api:app_dari_env --factory --port 8000
```

**Meja Pimpinan**
```bash
cd frontend
npm install
npm run dev
```
Buka `http://localhost:3000`, pilih "Diskominfo Kab. Sejahtera (SPJ)", masuk sebagai `sri` (bendahara) dengan sandi demo.

**WorkBuddy** — lihat [docs/workbuddy/prompt-spj-lengkap.md](docs/workbuddy/prompt-spj-lengkap.md) (membangun tim) dan [docs/workbuddy/sambung-gerbang-spj.md](docs/workbuddy/sambung-gerbang-spj.md) (konektor MCP ke gerbang).

> Sandi dan token di repo ini (`demo123`, `tok-spj`, dll.) hanya untuk demo lokal. Ganti sebelum dipakai di luar mesin sendiri.

## Prototipe awal: Agent Disposisi
Sebelum beralih ke SPJ, tim membangun prototipe disposisi surat (profil perusahaan & kecamatan). Kodenya masih ada dan memakai backend yang sama: `workbuddy/`, `demo/kecamatan/`, `testcases/`, `docs/superpowers/`. Gerbang persetujuan, audit log, dan Meja Pimpinan untuk AmanCair dikembangkan dari prototipe ini.
