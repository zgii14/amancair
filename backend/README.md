# Backend AmanCair

API REST, server MCP, dan log audit untuk AmanCair. Satu proses FastAPI melayani Meja Pimpinan (REST) dan konektor WorkBuddy (MCP). Kode prototipe disposisi surat juga masih ada di sini dan tetap teruji.

## Setup (Windows, Git Bash)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest
```

## Menjalankan API + MCP (satu proses)

```bash
DEMO_PASSWORD=ganti-ini MCP_TOKENS="tok-rina=perusahaan:rina,tok-camat=kecamatan:camat_andi" \
  .venv/Scripts/python -m uvicorn app.api:app_dari_env --factory --port 8000
```

- REST: `http://localhost:8000/api/...` (docs: `/docs`)
- MCP (untuk konektor kustom WorkBuddy): `http://localhost:8000/mcp/` dengan header `Authorization: Bearer tok-rina`
- WorkBuddy di laptop lain / backend remote: buka tunnel, mis. `cloudflared tunnel --url http://localhost:8000`

## MCP via stdio (bila WorkBuddy hanya mendukung stdio)

```bash
MCP_DEFAULT=perusahaan:rina .venv/Scripts/python -m app.mcp_server
```

Mode stdio dan API harus memakai `DATA_DIR` yang sama agar berbagi database.

## Variabel lingkungan

| Nama | Wajib | Keterangan |
|---|---|---|
| `DEMO_PASSWORD` | ya | Password login akun demo Meja Pimpinan |
| `MCP_TOKENS` | tidak | `token=profil:user,...`; tanpa ini MCP HTTP tidak di-mount |
| `FRONTEND_ORIGIN` | tidak | Origin Next.js untuk CORS, dipisah koma |
| `DATA_DIR` | tidak | Folder SQLite (default `data`) |
| `PROFIL_DIR` | tidak | Folder YAML profil (default `profil`) |
| `SPJ_DRAF_ROOT` | tidak | Folder draf SPJ yang ditulis tim agen WorkBuddy; tanpa ini tool `ajukan_spj` tidak aktif |
| `SPJ_SIAP_ROOT` | tidak | Folder tujuan pencairan (default `data/siap-cair`). Taruh di luar folder kerja agen |
| `SPJ_PROFIL` | tidak | Profil organisasi untuk SPJ (default `diskominfo`) |

## Gerbang persetujuan SPJ

Contoh menjalankan untuk AmanCair:

```bash
DEMO_PASSWORD=demo123 \
MCP_TOKENS="tok-spj=diskominfo:tim_spj" \
SPJ_DRAF_ROOT="D:/Agent 2/spj-agent/keluar/draf" \
  .venv/Scripts/python -m uvicorn app.api:app_dari_env --factory --port 8000
```

Alurnya:

1. Tim agen memanggil tool MCP `ajukan_spj` dengan nomor SPJ, total, dan daftar temuan.
2. Backend menghitung sendiri SHA-256 setiap berkas di `SPJ_DRAF_ROOT/<nomor>/` dan menyimpannya sebagai manifest. Status `PENDING`.
3. Bendahara membuka SPJ di Meja Pimpinan. SPJ berisiko tinggi (temuan KRITIS/TINGGI, perintah tersisip, atau total di atas Rp10 juta) wajib dicentang konfirmasinya.
4. Saat disetujui, backend menghitung ulang manifest. Kalau ada berkas yang berubah, bertambah, atau hilang, pencairan ditolak. Kalau cocok, berkas disalin byte per byte ke `SPJ_SIAP_ROOT/<nomor>/`.
5. Semua langkah tercatat di log audit berantai hash.

Akun agen (`pengelola_spj`) tidak punya hak menyetujui, jadi agen tidak bisa mencairkan sendiri.

Endpoint REST: `GET /api/spj`, `GET /api/spj/{nomor}`, `GET /api/spj/{nomor}/berkas/{path}`, `POST /api/spj/{nomor}/setujui`, `POST /api/spj/{nomor}/tolak`.

Catatan: `mcp` di-pin `<2` karena mcp 2.x mengganti nama `FastMCP` menjadi `MCPServer`.
