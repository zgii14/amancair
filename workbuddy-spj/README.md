# Agen SPJ Perjalanan Dinas — Tencent Cloud Hackathon Indonesia 2026

**DATA FIKTIF UNTUK DEMO**

Proyek ini adalah tim agen AI untuk otomatisasi Surat Pertanggungjawaban (SPJ) perjalanan dinas pegawai.

## Struktur Folder

```
spj-agent/
├── data/
│   ├── master/
│   │   ├── pegawai.xlsx       # 10 pegawai fiktif (termasuk 2 Budi)
│   │   ├── sbm.xlsx           # Pagu hotel & uang harian 4 provinsi
│   │   └── satker.json        # Data unit kerja fiktif
│   ├── spt/                   # 11 Surat Perintah Tugas (SPT)
│   ├── kasus/                 # 11 kasus bukti mentah
│   │   └── kasus-0XX/
│   │       ├── pesan_pegawai.txt   # Pesan chat informal
│   │       ├── tiket_berangkat.txt/pdf
│   │       ├── tiket_kembali.txt
│   │       ├── invoice_hotel.txt/pdf
│   │       ├── boarding_pass.txt
│   │       └── struk_*.txt    # Taksi, makan, dll.
│   └── libur/
│       └── libur.json         # Hari libur nasional demo
├── aturan/
│   └── bisnis.json            # Aturan R01–R10
├── log/
│   └── audit.jsonl            # Log audit (rekam jejak)
├── keluar/
│   ├── draf/                  # Hasil agen (belum disetujui)
│   └── siap-cair/             # HANYA diisi setelah SETUJUI SPJ-<nomor>
└── bukti/                     # Screenshot / demo
```

## 11 Kasus Uji

| Kasus | SPT | Pegawai | Provinsi | Skenario | Aturan |
|---|---|---|---|---|---|
| 001 | SPT-2026-001 | Budi Santoso (III/c) | DKI Jakarta | Normal, lengkap & sesuai | — |
| 002 | SPT-2026-002 | Dedi Kurniawan (III/d) | DKI Jakarta | Struk taksi ganda | R06 |
| 003 | SPT-2026-003 | Siti Aminah (II/d) | Bali | Hotel extend 1 hari di luar SPT | R01 |
| 004 | SPT-2026-004 | Rudi Hartono (IV/c) | DKI Jakarta | Hotel melebihi pagu SBM | R03 |
| 005 | SPT-2026-005a/b | Budi (ambigu) | DKI Jakarta | Dua Budi punya SPT ke Jakarta | Koordinator tanya |
| 006 | SPT-2026-006 | Lestari Dewi (III/a) | Bali | Perintah tersisip di invoice hotel | R09 |
| 007 | SPT-2026-007 | Nurul Hidayah (II/c) | Sulawesi Selatan | Nominal taksi tidak terbaca | R08 |
| 008 | SPT-2026-008 | Bayu Wijaya (II/b) | DKI Jakarta | Boarding pass atas nama orang lain | R02 |
| 009 | SPT-2026-009 | Ahmad Fauzi (IV/b) | DKI Jakarta | Dinas 15–18 Agustus, lewati 17 Agustus | R07 |
| 010 | SPT-2026-010 | Dedi Kurniawan (III/d) | Papua | Dinas 5 hari, total > Rp10 juta | R10 |
| 011 | SPT-2026-011 | Lestari Dewi (III/a) | DKI Jakarta | Struk taksi identik kasus-001, pegawai lain | R06 (lintas kasus) |

## 5 Penguatan Desain

Lihat `DESAIN.md` untuk detail lengkap.

1. **Timeline & Kontradiksi** — Auditor menyusun kronologi per kasus dan menandai pertentangan antar dokumen.
2. **Jejak Per Angka** — Setiap nominal di rekap.xlsx membawa file sumber, kutipan teks, kode aturan, dan rumus hitung.
3. **Level Risiko Temuan** — KRITIS, TINGGI, SEDANG, RENDAH. Layar konfirmasi diurutkan dari paling kritis.
4. **Struk Ganda Lintas Kasus** — Indeks sidik bukti (fingerprint) untuk semua kasus; agen hanya terima sinyal boolean tanpa melihat data kasus lain.
5. **Hitungan Terukur** — Semua perhitungan menggunakan skrip/rumus yang bisa diulang, bukan tebakan LLM.

## Aturan Tambahan

- **Tiket pesawat** dibayar sesuai bukti riil (tanpa pagu) selama nama penumpang dan tanggal keberangkatan sesuai SPT.
- **R05 (Pagu Transport Lokal)** dihitung per struk/trip (per perjalanan dalam satu struk).
- **R11** — Biaya makan sudah termasuk uang harian (R04). Struk makan dicatat sebagai bukti pendukung; nilai_dibayar = 0; level risiko RENDAH.

## Tabel Cek Silang Kasus

| Kasus | Pegawai | Golongan | Provinsi | Pagu Hotel/malam | Biaya Hotel/malam (incl. pajak) | Pagu Taksi | Taksi Diajukan | Aturan Terpicu |
|---|---|---|---|---|---|---|---|---|
| 001 | Budi Santoso | III/c | DKI Jakarta | Rp 800.000 | Rp 770.000 | Rp 250.000 | Rp 210.000 | — |
| 002 | Dedi Kurniawan | III/d | DKI Jakarta | Rp 800.000 | Rp 572.000 | Rp 250.000 | Rp 170.000 | R06 (struk ganda) |
| 003 | Siti Aminah | II/d | Bali | Rp 550.000 | Rp 528.000 | Rp 200.000 | Rp 145.000 | R01 (hotel di luar SPT) |
| 004 | Rudi Hartono | IV/c | DKI Jakarta | Rp 1.000.000 | **Rp 1.320.000** | Rp 250.000 | Rp 230.000 | **R03 (melebihi pagu)** |
| 005 | Budi (ambigu) | ? | DKI Jakarta | 800rb / 1jt | Rp 770.000 | Rp 250.000 | Rp 165.000 | Koordinator tanya |
| 006 | Lestari Dewi | III/a | Bali | Rp 750.000 | Rp 748.000 | Rp 200.000 | — | R09 (perintah tersisip) |
| 007 | Nurul Hidayah | II/c | Sulawesi Selatan | Rp 450.000 | — | Rp 150.000 | tidak terbaca | R08 (tidak terbaca) |
| 008 | Bayu Wijaya | II/b | DKI Jakarta | Rp 600.000 | Rp 572.000 | Rp 250.000 | Rp 155.000 | R02 (nama beda) |
| 009 | Ahmad Fauzi | IV/b | DKI Jakarta | Rp 1.000.000 | Rp 990.000 | Rp 250.000 | Rp 250.000 | R07 (hari libur) |
| 010 | Dedi Kurniawan | III/d | Papua | Rp 1.100.000 | Rp 1.100.000 | Rp 400.000 | Rp 350.000 + Rp 280.000 | R10 (total > Rp 10 juta) |
| 011 | Lestari Dewi | III/a | DKI Jakarta | — | — | Rp 250.000 | Rp 210.000 | R06 (ganda lintas kasus) |

*Catatan: Biaya hotel per malam (incl. pajak) = total invoice ÷ jumlah malam. Pagu taksi per struk/trip.*

## 5 Aturan Akuntabilitas

1. **SUMBER** — setiap angka menunjuk ke file bukti asal.
2. **IZIN** — agen hanya membaca folder kasus aktif.
3. **PERSETUJUAN** — tidak ada file dipindahkan ke `siap-cair/` sebelum bendahara mengetik `SETUJUI SPJ-<nomor>`.
4. **BATASAN** — bila bukti tidak terbaca, status "perlu_cek_manusia", tidak ditebak.
5. **REKAM JEJAK** — setiap langkah dicatat ke `log/audit.jsonl`.

## Cara Menyetujui SPJ

Ketik di chat:
```
SETUJUI SPJ-<nomor>
```

Untuk menolak:
```
TOLAK SPJ-<nomor> <alasan>
```

## Rumus Hash Log Audit (log/audit.jsonl)

Setiap baris JSON di log audit memiliki rantai hash SHA-256 yang bisa diverifikasi manual:

1. Baris pertama: `prev_hash = "0" * 64` (64 karakter nol).
2. Untuk setiap baris: hapus field `hash` dan `prev_hash` dari objek JSON.
3. Urutkan key secara alfabet (`sort_keys=True`).
4. Serialize ke string JSON UTF-8 (`ensure_ascii=False`).
5. Hitung: `hash = SHA-256(prev_hash + payload_json)`.
6. Simpan `prev_hash` dan `hash` ke baris JSON.
7. Baris berikutnya menggunakan `hash` baris ini sebagai `prev_hash`.

Contoh verifikasi Python:
```python
import hashlib, json
payload = json.dumps({k:v for k,v in baris.items() if k not in ("hash","prev_hash")}, ensure_ascii=False, sort_keys=True)
computed = hashlib.sha256(baris["prev_hash"] + payload).hexdigest()
assert computed == baris["hash"]
```

Atau jalankan: `python tools/verifikasi_log.py log/audit.jsonl`
