# Menyambungkan WorkBuddy ke Gerbang Persetujuan SPJ

Tujuan: WorkBuddy hanya **mengajukan** draf SPJ; **bendahara menyetujui di Meja Pimpinan**; **backend** yang mencairkan
(menyalin ke `D:\HACKATHON2\backend\data\siap-cair`, di luar folder kerja WorkBuddy).

## 1. Nyalakan backend + Meja Pimpinan
Jalankan konfigurasi `backend` dan `frontend` di `.claude/launch.json`, atau dari terminal:

```bash
cd backend
DEMO_PASSWORD=demo123 MCP_TOKENS="tok-spj=diskominfo:tim_spj" SPJ_DRAF_ROOT="D:/Agent 2/spj-agent/keluar/draf" SPJ_SIAP_ROOT="D:/HACKATHON2/backend/data/siap-cair" .venv/Scripts/python -m uvicorn app.api:app_dari_env --factory --port 8000
```

```bash
cd frontend && npm run dev
```

Meja Pimpinan: `http://localhost:3000` → pilih "Diskominfo Kab. Sejahtera (SPJ)", ID `sri`, sandi demo.

## 2. Tambah konektor MCP di WorkBuddy
Diuji di WorkBuddy AI v5.9.4. Ada dua cara:

**Lewat aplikasi:** sidebar **Experts · Skills · Connectors** → tab **Connectors** → tombol **Custom connectors** (kanan atas) → **MCP Server Management** → **Add MCP**. Isi:
- Tipe: streamable HTTP
- URL: `http://localhost:8000/mcp/`
- Header: `Authorization: Bearer tok-spj`

**Lewat berkas plugin Expert Team:** letakkan `.mcp.json` (pakai titik di depan, bukan `mcp.json`) di folder plugin, misalnya `%USERPROFILE%\.workbuddy-ai\plugins\marketplaces\my-experts\plugins\spj-agent-team\.mcp.json`, lalu tutup WorkBuddy sepenuhnya dan buka lagi:

```json
{
  "mcpServers": {
    "amancair": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp/",
      "headers": { "Authorization": "Bearer tok-spj" }
    }
  }
}
```

Hasil yang benar: di MCP Server Management, `amancair` bertitik hijau dengan **7/7 tools enabled** (termasuk `ajukan_spj` dan `periksa_aturan`), dan log backend menampilkan `POST /mcp/ 200`.

Pastikan folder yang diizinkan WorkBuddy hanya `D:\Agent 2` (bukan `D:\HACKATHON2`).

## 3. Prompt untuk WorkBuddy (ubah aturan persetujuan)

```
Mulai sekarang persetujuan SPJ TIDAK lagi lewat chat. Perbarui skill Koordinator dan Penyusun
(sinkronkan agents/ Expert Team dan export/):

1. Setelah layar konfirmasi + manifest selesai di keluar/draf/SPJ-<nomor>/, Koordinator memanggil tool MCP
   ajukan_spj dengan: nomor, pegawai, tujuan, tanggal_spt, total_diajukan, total_dibayar,
   temuan (level, aturan, deskripsi, sumber), perintah_tersisip.
2. Setelah diajukan, JANGAN mengubah berkas apa pun di folder draf itu. Bila perlu revisi, ubah lalu panggil
   ajukan_spj lagi (versi baru).
3. Agen TIDAK PERNAH menulis ke folder siap-cair mana pun dan tidak memproses pesan "SETUJUI ..." di chat.
   Bila saya mengetik persetujuan di chat, jawab: "Persetujuan dilakukan bendahara di Meja Pimpinan."
4. Catat pemanggilan ajukan_spj (nomor, versi, manifest_hash dari respons) di log/audit.jsonl.

Uji dengan mengajukan SPJ-2026-002 lewat ajukan_spj, lalu tampilkan respons tool-nya.
```

## 4. Bukti untuk submission
- Screenshot WorkBuddy memanggil `ajukan_spj` dan responsnya ("BELUM dicairkan").
- Screenshot Meja Pimpinan: daftar SPJ, lembar dengan temuan, cap "DICAIRKAN".
- Uji keamanan: ubah satu berkas draf setelah diajukan → Setujui ditolak "Berkas berubah sejak diajukan".
