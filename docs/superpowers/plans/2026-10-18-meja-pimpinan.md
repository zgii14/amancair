# Meja Pimpinan (Next.js) Implementation Plan

**Goal:** UI web tempat pimpinan meninjau rencana aksi yang diajukan agent dan memutuskan Setujui / Tolak, dengan undo 60 detik, riwayat terkirim, dan audit log.

**Architecture:** Next.js 15 App Router (`frontend/`), komponen client yang memanggil REST backend lewat rewrites `/api/*` → `BACKEND_URL` sehingga cookie `sid` same-origin. Tanpa state global; tiap halaman fetch sendiri.

**Tech Stack:** Next.js 15, React 19, TypeScript, CSS global dengan token (tanpa Tailwind), Google Fonts lewat `next/font` (Bitter, Public Sans, IBM Plex Mono).

## Global Constraints
- Kontrak API mengikuti `backend/app/api.py` (lihat Plan 1 Task 8).
- Bahasa Indonesia, sentence case, label tombol = aksi ("Setujui", "Tolak", "Batalkan pengiriman").
- Mobile-first (lebar 360px), fokus keyboard terlihat, `prefers-reduced-motion` dihormati.
- Desain: "lembar disposisi" — palet `--meja #E6EBE3`, `--kertas #FFFFFF`, `--tinta #1F2A44`, `--stempel #4B3FA8`, `--merah #B5432F`, `--hijau #2F6B4F`, `--garis #C3CCBE`.
- Label asal: pimpinan (hijau), direktori (tinta), surat (merah + ⚠).

## File Structure
```
backend/scripts/seed_demo.py         data demo (4 rencana PENDING per profil)
frontend/next.config.ts              rewrites /api → BACKEND_URL
frontend/app/layout.tsx              font + shell
frontend/app/globals.css             token & komponen
frontend/lib/api.ts                  fetch wrapper + tipe
frontend/components/Header.tsx       identitas user + navigasi + keluar
frontend/components/Asal.tsx         chip label asal
frontend/app/login/page.tsx          login
frontend/app/page.tsx                antrean PENDING
frontend/app/rencana/[id]/page.tsx   lembar disposisi + keputusan + undo
frontend/app/riwayat/page.tsx        rencana selesai + terkirim
frontend/app/audit/page.tsx          audit log + verifikasi rantai
```

## Tasks
1. **Seed demo backend** — `seed_demo.py` membuat rencana: notulen ke Budi (normal), notulen berisi perintah tersisip + penerima dari surat (peringatan), undangan eksternal (risiko tinggi), surat rahasia; profil kecamatan: disposisi undangan Dinas PMD. Verifikasi: `GET /api/rencana` mengembalikan data.
2. **Scaffold + proxy + token desain** — rewrites, font, globals.css. Verifikasi: `npm run build`.
3. **Login + header + antrean** — 401 → redirect `/login`; kartu antrean menampilkan perihal, pengirim, badge risiko & jumlah peringatan; keadaan kosong mengarahkan ke cara mengajukan lewat WorkBuddy.
4. **Lembar disposisi** — kop (perihal, pengirim, sifat, diterima), ringkasan + kutipan sumber, banner peringatan, kotak per aksi (jenis, kepada + chip asal, waktu dengan zona, isi, instruksi baku tercentang, tenggat), catatan checker, hash rencana. Bar keputusan lengket: Tolak (wajib alasan) / Setujui (risiko tinggi → konfirmasi tambahan). Tangani 403/409/428.
5. **Cap & undo** — setelah Setujui: cap "DISETUJUI" + hitung mundur ke `bisa_undo_sampai`, tombol "Batalkan pengiriman"; setelah 0 → "Terkirim".
6. **Riwayat & audit** — daftar rencana non-PENDING + item terkirim; audit log dengan status rantai (utuh / rusak di seq N).
7. **Uji end-to-end** — backend lokal + seed + `npm run dev`; alur login → setujui → undo → setujui lain → terkirim → audit, cek di lebar 375px; `npm run build` & `npm run lint` bersih.
