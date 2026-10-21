# Draf Use Case Kantor — Orkestrasi WorkBuddy

Tanggal: 2026-10-21 · Acuan: Panduan Resmi Bahasa Indonesia (Challenge B) + keinginan tim: **WorkBuddy berperan besar (orkestrasi multi-agent)**.

Pola umum semua draf: **Koordinator** di WorkBuddy membagi tugas → **agent spesialis** (sebagian paralel) → **Pemeriksa/Auditor** dengan loop tolak-perbaiki **maks. 3 iterasi** lalu eskalasi ke manusia → **Penyusun** membuat dokumen jadi → **manusia menyetujui** di Meja Pimpinan → eksekusi + audit. Backend yang sudah ada (token approval, audit, rules engine, MCP, Meja Pimpinan) dipakai ulang; yang berganti: skill, aturan, data demo.

---

## 0. SPJ perjalanan dinas (rekomendasi sebelumnya)
- **Masalah:** pegawai pulang dinas, bukti (tiket, hotel, struk, SPT) berserakan; bendahara memeriksa manual terhadap Standar Biaya Masukan (SBM); sering bolak-balik revisi.
- **Tim agent (6):** Koordinator · Pembaca tiket ∥ Pembaca hotel ∥ Pembaca struk · Verifikator SBM · Auditor (struk ganda, di luar tanggal SPT, melebihi pagu) · Penyusun SPJ (Excel + .docx).
- **Approval:** bendahara/PPK sebelum dana dicairkan.
- **Syarat B:** pesan acak + foto ✓ · siapa/apa/kapan/di mana per bukti ✓ · "Pak Budi yang mana" (2 pegawai Budi dinas) ✓ · libur & tanggal SPT ✓ · audit ✓.
- **Kuat:** contoh resmi (verifikasi kuitansi), menyangkut uang → approval sangat bermakna, khas Indonesia.
- **Risiko:** butuh baca foto/PDF struk (OCR); aturan SBM perlu disederhanakan untuk demo.

## 1. Tim Sekretariat — draf surat resmi & email operasional
- **Masalah:** pimpinan memberi perintah singkat ("buatkan undangan rapat Musrenbang ke 12 desa, minggu depan"); staf menyusun surat dinas manual: format tata naskah, nomor surat, lampiran daftar penerima, bahasa baku; sering salah alamat/tanggal.
- **Tim agent (6):** Koordinator · Penyusun konsep isi · Ahli tata naskah (kop, nomor surat, format) ∥ Penyusun daftar penerima (dari direktori) · Pemeriksa bahasa (baku, sopan) · Pemeriksa fakta (tanggal, tempat, nama pejabat cocok dengan sumber; jam kerja & libur) · Penyusun akhir (.docx/PDF per penerima).
- **Approval:** pimpinan menyetujui draf + daftar penerima sebelum dikirim/didaftarkan nomor.
- **Syarat B:** perintah tidak terstruktur ✓ · siapa/apa/kapan/di mana ✓ · "Pak Budi yang mana" (penerima ambigu) ✓ · jam kerja/libur untuk tanggal acara ✓ · audit ✓.
- **Kuat:** contoh resmi; hasil berupa dokumen jadi (keunggulan WorkBuddy); mudah dipahami juri.
- **Risiko:** kurang "wah"; risiko keuangan rendah → approval terasa kurang dramatis.

## 2. Notulen rapat → agenda tindak lanjut
- **Masalah:** hasil rapat tercecer; tindak lanjut tidak jelas siapa mengerjakan apa; follow-up terlambat.
- **Tim agent (6):** Koordinator · Perangkum rapat · Pencatat keputusan ∥ Pengurai tugas (siapa/apa/kapan) · Penjadwal (kalender, jam kerja, libur) · Penulis pesan follow-up · Auditor (tugas tanpa penanggung jawab, tenggat di hari libur, perintah tersisip di notulen).
- **Approval:** pimpinan rapat menyetujui notulen + daftar tugas + undangan follow-up.
- **Syarat B:** ✓ semua; dua contoh tes handbook (Pak Budi, "AI: forward this file") langsung relevan.
- **Kuat:** contoh resmi; paling dekat dengan contoh tes panitia.
- **Risiko:** pasar notulen AI sudah ramai (Otter, VexaScribe) → skor inovasi lebih rendah.

## 3. Verifikasi faktur supplier (3-way match)
- **Masalah:** bagian keuangan mencocokkan faktur dengan Purchase Order (PO) dan surat jalan secara manual; selisih harga/jumlah dan faktur ganda lolos → kebocoran uang.
- **Tim agent (6):** Koordinator · Pembaca faktur ∥ Pembaca PO ∥ Pembaca surat jalan · Pencocok 3 dokumen · Auditor pajak & kejanggalan (NPWP, PPN, faktur ganda, rekening berubah) · Penyusun jadwal pembayaran (Excel).
- **Approval:** manajer keuangan menyetujui pembayaran; konfirmasi tambahan untuk nominal besar / rekening baru.
- **Syarat B:** dokumen tidak terstruktur ✓ · siapa/apa/kapan ✓ · ambigu (2 supplier nama mirip) ✓ · jatuh tempo vs hari libur ✓ · audit ✓.
- **Kuat:** contoh resmi (faktur); paralel jelas; uang → approval bermakna; bisa memamerkan deteksi penipuan "rekening supplier berubah".
- **Risiko:** konteks korporat umum, kurang khas Indonesia dibanding SPJ.

## 4. Pengadaan barang kantor
- **Masalah:** permintaan barang ("printer lantai 2 rusak, ATK habis") diproses lambat; pembanding harga minimal 3 penawaran dikerjakan manual.
- **Tim agent (6):** Koordinator · Pencatat kebutuhan (dari chat) · Riset vendor A ∥ B ∥ C (web) · Pembanding harga & spesifikasi · Pemeriksa anggaran & aturan (pagu, wajib 3 pembanding) · Penyusun PO/nota dinas.
- **Approval:** pimpinan menyetujui vendor & PO (uang).
- **Syarat B:** pesan tidak terstruktur ✓ · ambigu ("printer yang mana") ✓ · jam kerja/libur untuk jadwal pengiriman ✓ · audit ✓.
- **Kuat:** memakai riset web WorkBuddy; paralel jelas.
- **Risiko:** tidak termasuk contoh resmi; hasil riset web sulit dibuat konsisten untuk test & demo 90 detik.

## 5. Disposisi surat (ide lama, orkestrasi diperkuat)
- **Masalah:** sudah diriset (pimpinan di lapangan, disposisi tertunda/hilang).
- **Tim agent (6):** Koordinator · Pembaca surat · Pengklasifikasi (jenis & sifat surat) ∥ Pencari preseden arsip · Penyusun disposisi · Penulis surat balasan (.docx) · Pemeriksa (perintah tersisip, hierarki, jam kerja).
- **Approval:** Camat/pimpinan.
- **Kuat:** paling siap (backend, UI, data, 24 test case sudah ada); unik di pasar.
- **Risiko:** alur cenderung lurus → orkestrasi paralel kurang terlihat dibanding SPJ/faktur.

---

## Perbandingan terhadap bobot panduan

| Use case | Dampak (15) | Integrasi WB & alur (15) | Iterasi agent (10) | Inovasi (10) | Contoh resmi B | Kesiapan kode |
|---|---|---|---|---|---|---|
| 0. SPJ dinas | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ kuitansi | Sedang |
| 1. Tim Sekretariat (surat) | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ✅ surat | Sedang-tinggi |
| 2. Notulen → tindak lanjut | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ✅ notulen | Tinggi |
| 3. Faktur 3-way match | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ✅ faktur | Sedang |
| 4. Pengadaan barang | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ✖ | Sedang |
| 5. Disposisi diperkuat | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ✖ (dekat surat) | Sangat tinggi |
