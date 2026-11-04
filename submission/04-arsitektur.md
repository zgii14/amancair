# Diagram Arsitektur — AmanCair

## 1. Alur dari pegawai sampai bendahara

```mermaid
flowchart LR
    P["Pegawai<br/>mengunggah bukti di web"] --> BE[("Backend AmanCair<br/>FastAPI + SQLite")]
    BE -->|"skrip jembatan<br/>menyalin bukti"| WB["WorkBuddy<br/>Expert Team (laptop/PC pengelola SPJ)"]
    WB -->|"MCP: periksa_aturan,<br/>ajukan_spj"| BE
    WB -->|"jembatan: progres<br/>dan draf"| BE
    BE --> MP["Meja Pimpinan<br/>dasbor bendahara"]
    MP -->|"Setujui untuk dibayar / Tolak"| BE
```

## 2. Orkestrasi tim agen (di dalam WorkBuddy)

```mermaid
flowchart TD
    IN["Bukti + SPT kasus"] --> K
    subgraph WB["Tencent Cloud WorkBuddy — Expert Team 'SPJ Agent Team'"]
        K["Koordinator<br/>identifikasi pegawai & SPT<br/>bertanya bila ambigu"]
        K -->|paralel| PT["Pembaca Tiket"]
        K -->|paralel| PH["Pembaca Hotel"]
        K -->|paralel| PS["Pembaca Struk"]
        PT --> V["Pemeriksa Batas Biaya<br/>memanggil periksa_aturan"]
        PH --> V
        PS --> V
        V --> A["Pemeriksa Ulang (Auditor)<br/>cocokkan dengan bukti asli<br/>temuan AUDITOR bila perlu"]
        A -->|"salah baca (maks. 3 iterasi)"| K
        A -->|lolos| D["Penyusun Dokumen<br/>skrip templat → ajukan_spj"]
    end
    K -. "ambigu (mis. dua Budi)" .-> H1(("Pengelola SPJ<br/>menjawab"))
    V <-->|"hitungan R01–R11"| KAL["Kalkulator aturan<br/>(kode, di backend)"]
```

## 3. Batas kepercayaan dan gerbang persetujuan

```mermaid
flowchart LR
    subgraph AGEN["Zona agen — folder kerja WorkBuddy"]
        D["keluar/draf/SPJ-xxxx/"]
        T["Tool MCP ajukan_spj"]
    end
    subgraph BE["Zona backend"]
        H["Hitung sidik SHA-256<br/>semua berkas draf"]
        C{"Angka & temuan sama<br/>dengan kalkulator?"}
        G{"Sidik masih sama<br/>saat disetujui?"}
        S["Salin berkas identik<br/>ke folder di luar zona agen"]
        L[("Log audit<br/>hash berantai")]
    end
    subgraph MP["Meja Pimpinan"]
        F["Daftar periksa berkas fisik<br/>SPPD bercap · bukti asli ·<br/>laporan · meterai > Rp5 jt"]
        B["Bendahara:<br/>Setujui untuk dibayar / Tolak"]
    end
    D --> T -->|"HTTP + bearer token"| H --> C
    C -->|tidak| R["Ditandai perlu<br/>persetujuan khusus"] --> F
    C -->|ya| F
    F --> B -->|Setujui| G
    G -->|ya| S --> L
    G -->|tidak| X["Ditolak:<br/>berkas berubah"] --> L
```

**Garis batas:** agen hanya bisa menghitung lewat kalkulator dan *mengajukan*. Penyalinan berkas yang disetujui hanya dilakukan backend setelah bendahara mencentang daftar periksa dan menekan Setujui, ke folder di luar jangkauan WorkBuddy.

## 4. Komponen

| Komponen | Teknologi | Tanggung jawab |
|---|---|---|
| Tim agen | WorkBuddy Expert Team, 7 agen dengan instruksi masing-masing | Membaca, menilai, bertanya, memeriksa ulang, menyusun |
| Kalkulator aturan | Tool MCP `periksa_aturan` di backend | Hitungan R01–R11, struk ganda lintas SPJ, uang harian |
| Templat dokumen | `tools/susun_dokumen.py` (openpyxl, python-docx) | Rekap Excel, draf SPJ Word, ringkasan pemeriksaan bergaya dinas |
| Jembatan | `scripts/jembatan_workbuddy.py` | Mengambil pengajuan pegawai, mengirim progres agen, mengunggah draf |
| Backend | Python, FastAPI, FastMCP, SQLite, pytest (167 tes) | Gerbang SPJ, audit hash berantai, perbandingan dengan kalkulator |
| Meja Pimpinan | Next.js | Dasbor bendahara, halaman pegawai, papan proses pemeriksaan |
| Data demo | Excel/JSON/TXT/PDF fiktif | Pegawai, SBM, SPT, libur, 11 kasus bukti |

## 5. Keputusan desain & trade-off

| Keputusan | Alasan | Konsekuensi |
|---|---|---|
| Model untuk membaca dan menilai; kode untuk menghitung | Saat uji, model salah hitung, melewatkan aturan, dan menulis angka dari ingatan | Kasus selesai 4–9 menit (dulu 17–25); dua kasus yang dulu gagal kini lolos |
| Persetujuan di backend, bukan di agen | Agen pernah menyimulasikan kerja tim, menyalin versi berkas berbeda, dan menulis persetujuan atas nama bendahara meski dilarang | Backend dan konektor MCP harus berjalan |
| Pengajuan dibandingkan dengan hasil kalkulator | Agen tidak bisa diam-diam mengubah angka atau membuang temuan penting | Selisih apa pun membuat SPJ perlu persetujuan khusus |
| Auditor boleh menambah temuan berlabel `AUDITOR` | Ada hal yang tidak bisa dihitung kode; saat uji, Auditor justru menemukan dua celah di kalkulator | Temuan agen dan temuan kode dibedakan di layar |
| Daftar periksa berkas fisik oleh manusia | AI hanya melihat salinan digital, tidak bisa menjamin SPPD bercap atau bukti asli | Satu langkah tambahan untuk bendahara |
| Agen hanya jalan saat PC pengelola menyala | WorkBuddy adalah aplikasi desktop tanpa API masuk | Pengajuan pegawai menunggu di antrean sampai PC menyala; web tetap bisa diakses kapan saja |
| Sidik versi seluruh berkas | Persetujuan harus atas berkas yang persis sama | Revisi sekecil apa pun menjadi pengajuan versi baru |
| Data SBM fiktif dan disederhanakan | Panitia mengizinkan data dummy | Perlu diganti SBM resmi saat implementasi nyata |
