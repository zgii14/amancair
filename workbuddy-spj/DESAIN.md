# Desain Agen SPJ — 5 Penguatan Tambahan

**DATA FIKTIF UNTUK DEMO**

Dokumen ini melengkapi rencana Tahap 2–4 dengan 5 penguatan desain yang disepakati sebelum eksekusi.

---

## 1. TIMELINE & KONTRADIKSI (Auditor)

### Tanggung Jawab
Auditor wajib menyusun **kronologi per kasus** dari semua dokumen yang terdeteksi:
- SPT (tanggal berangkat, tanggal kembali)
- Tiket pesawat/kereta (tanggal keberangkatan, tanggal kembali)
- Invoice hotel (check-in, check-out)
- Struk taksi/makan/transport (tanggal struk)

### Format Output Timeline
```json
{
  "kasus_id": "kasus-001",
  "timeline": [
    {"tanggal": "2026-10-05", "event": "SPT_mulai", "sumber": "SPT-2026-001.json"},
    {"tanggal": "2026-10-05", "event": "tiket_berangkat", "sumber": "tiket_berangkat.txt"},
    {"tanggal": "2026-10-05", "event": "hotel_checkin", "sumber": "invoice_hotel.txt"},
    {"tanggal": "2026-10-05", "event": "taksi_bandara", "sumber": "struk_taksi_1.txt"},
    {"tanggal": "2026-10-06", "event": "struk_makan", "sumber": "struk_makan_1.txt"},
    {"tanggal": "2026-10-08", "event": "hotel_checkout", "sumber": "invoice_hotel.txt"},
    {"tanggal": "2026-10-08", "event": "tiket_kembali", "sumber": "tiket_kembali.txt"},
    {"tanggal": "2026-10-08", "event": "SPT_selesai", "sumber": "SPT-2026-001.json"}
  ],
  "kontradiksi": [
    {
      "tipe": "hotel_checkin_sebelum_SPT",
      "tingkat": "TINGGI",
      "deskripsi": "Hotel check-in 11 Okt padahal SPT mulai 12 Okt",
      "kutipan_a": {"file": "invoice_hotel.txt", "teks": "Check-in: 11 Oktober 2026"},
      "kutipan_b": {"file": "SPT-2026-00X.json", "teks": "tanggal_berangkat: 2026-10-12"},
      "aturan": "R01"
    }
  ]
}
```

### Aturan Kontradiksi yang Diperiksa
- Hotel check-in < SPT berangkat → kontradiksi (tanpa kelonggaran)
- Hotel check-out > SPT kembali → kontradiksi
- Tiket berangkat < SPT berangkat (boleh H-1 untuk tiket berangkat sesuai R01)
- Tiket kembali > SPT kembali
- Struk tanggal di luar rentang SPT (R01)
- Hotel lama menginap tidak cocok dengan SPT lama hari

---

## 2. JEJAK PER ANGKA (Penyusun SPJ → rekap.xlsx)

Setiap baris di rekap.xlsx wajib membawa kolom:

| Kolom | Keterangan |
|---|---|
| `id_bukti` | B01, B02, dst. |
| `file_sumber` | Path file asal |
| `kutipan_teks` | Teks persis yang dibaca dari bukti |
| `kode_aturan` | R01, R02, dst. |
| `rumus_hitung` | Formula yang bisa diulang, mis. `=MIN(diajukan; pagu)` atau `3 malam × 800000 = 2400000; diajukan 2640000; dipotong 240000` |
| `nilai_diajukan` | Angka dari bukti |
| `nilai_dibayar` | Angka setelah verifikasi |
| `selisih` | `nilai_diajukan - nilai_dibayar` |
| `yakin_pembaca` | tinggi / sedang / rendah |

### Prinsip
- Tidak ada angka "dihitung di kepala" — semua perhitungan harus tertulis sebagai rumus/string yang bisa diaudit.
- Auditor memverifikasi bahwa rumus_hitung konsisten dengan aturan.

---

## 3. LEVEL RISIKO TEMUAN

Setiap temuan diberi level:

| Level | Kriteria | Contoh |
|---|---|---|
| **KRITIS** | Identitas tidak cocok, struk ganda, perintah tersisip, boarding pass nama orang lain | R02 (nama beda), R06 (ganda), R09 (perintah tersisip) |
| **TINGGI** | Melebihi pagu, tanggal di luar SPT, hotel check-in sebelum SPT | R01 (di luar SPT), R03 (melebihi pagu) |
| **SEDANG** | Bukti wajib hilang, nominal tidak terbaca, format aneh | R08 (tidak terbaca) |
| **RENDAH** | Format/penamaan file tidak standar, pesan pegawai tidak cocok bukti | — |

### Dampak ke UI
- Layar konfirmasi bendahara **diurutkan dari KRITIS ke RENDAH**.
- Tombol "SETUJUI" tidak aktif selama ada temuan KRITIS yang belum diselesaikan (eskalasi atau ditandai "diabaikan setelah eskalasi").

---

## 4. STRUK GANDA LINTAS KASUS

### Indeks Sidik Bukti (Fingerprint)
Saat Pembaca selesai membaca satu struk, Koordinator membuat **sidik**:
```json
{
  "sidik": {
    "tanggal": "2026-10-05",
    "nomor_transaksi": "TX-884721",
    "nominal": 210000,
    "merchant": "BLUE BIRD TAXI",
    "rute": "Bandara Soekarno-Hatta - Hotel Grand Java"
  },
  "kasus_asal": "kasus-001",
  "file_asal": "struk_taksi_1.txt",
  "pegawai": "Budi Santoso"
}
```

### Batasan Privasi (Aturan IZIN)
- Saat memproses kasus-011, agen hanya menerima sinyal boolean: **"sidik ini pernah diajukan di SPJ lain"**.
- Agen **tidak boleh melihat** kasus_asal, file_asal, atau nama pegawai kasus lain.
- Hanya Koordinator yang mengetahui "pasangan"-nya, dan hanya untuk keperluan laporan struk ganda.

### Kasus-011 (Baru)
- Pegawai: Lestari Dewi (SPT-2026-011)
- Struk taksi: **identik persis** dengan kasus-001 (TX-884721, 5 Okt 2026, Rp 210.000)
- Nama file berbeda: `struk_bandara_hotel.txt`
- Tujuan: menguji deteksi ganda lintas kasus tanpa bocor data.

---

## 5. HITUNGAN TIDAK DISERAHKAN KEPADA TEBAKAN

### Prinsip
Semua penjumlahan, selisih, jumlah malam, dan jumlah hari dihitung dengan **skrip/rumus yang bisa diulang**, bukan dihitung bebas dalam jawaban LLM.

### Implementasi
- Koordinator menjalankan fungsi `hitung_malam(check_in, check_out)` → integer
- Koordinator menjalankan fungsi `hitung_hari_spt(berangkat, kembali)` → integer
- Verifikator menggunakan rumus Excel/string: `=MIN(diajukan; pagu_sbm)`
- Penyusun SPJ menggunakan `openpyxl` untuk menulis formula Excel ke `rekap.xlsx` (bukan nilai hardcoded)
- Auditor memverifikasi ulang dengan skrip independen

### Contoh Formula di rekap.xlsx
```
=MIN(E2, VLOOKUP(...))          ; dipotong ke pagu SBM
=DATEDIF(check_in, check_out, "D")  ; jumlah malam
=SUMIF(status, "sesuai", nominal)   ; total yang dibayar
```

---

## Ringkasan Perubahan per Agen

| Agen | Penguatan |
|---|---|
| **Koordinator** | Menjalankan fungsi hitung (malam, hari), mengelola indeks sidik lintas kasus, menggabungkan timeline |
| **Pembaca Tiket/Hotel/Struk** | Menghasilkan sidik (nomor transaksi + tanggal + nominal + merchant) untuk indeks ganda |
| **Verifikator SBM** | Menggunakan rumus terukur, menulis `rumus_hitung` per item |
| **Auditor** | Menyusun timeline, mendeteksi kontradiksi antar dokumen, menetapkan level risiko |
| **Penyusun SPJ** | Menulis formula Excel (bukan hardcoded) ke `rekap.xlsx`, menambah kolom jejak per angka |

---

## Ringkasan Perubahan Output

| Output | Perubahan |
|---|---|
| `rekap.xlsx` | Tambah kolom: `file_sumber`, `kutipan_teks`, `kode_aturan`, `rumus_hitung`, `selisih`, `yakin_pembaca` |
| `timeline.json` | Baru: kronologi per kasus dengan kontradiksi |
| `laporan_audit.jsonl` | Tambah field: `level_risiko`, `sidik` |
| Layar konfirmasi | Diurutkan level risiko (KRITIS → RENDAH), blok SETUJUI bila ada KRITIS |
| `keluar/siap-cair/` | Tetap kosong sampai bendahara mengetik `SETUJUI SPJ-<nomor>` |
