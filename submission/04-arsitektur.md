# Diagram Arsitektur — AmanCair

## 1. Orkestrasi tim agen (di dalam WorkBuddy)

```mermaid
flowchart TD
    IN["Pesan pegawai + folder bukti<br/>(tiket, invoice hotel, struk, boarding pass)"] --> K
    subgraph WB["Tencent Cloud WorkBuddy — Expert Team 'SPJ Agent Team'"]
        K["Koordinator<br/>identifikasi pegawai & SPT<br/>bertanya bila ambigu"]
        K -->|paralel| PT["Pembaca Tiket"]
        K -->|paralel| PH["Pembaca Hotel"]
        K -->|paralel| PS["Pembaca Struk"]
        PT --> V["Verifikator SBM<br/>R01–R11, rumus terukur"]
        PH --> V
        PS --> V
        V --> A["Auditor independen<br/>kronologi, kontradiksi, struk ganda,<br/>perintah tersisip, level risiko"]
        A -->|"kesalahan kerja agen<br/>(maks. 3 iterasi)"| K
        A -->|lolos / temuan asli| P["Penyusun SPJ<br/>rekap.xlsx · draf_spj.docx<br/>timeline.json · layar konfirmasi"]
    end
    K -. "ambigu (mis. dua Budi)" .-> H1(("Bendahara<br/>menjawab"))
    A -. ">3 iterasi" .-> H2(("Eskalasi<br/>ke manusia"))
```

## 2. Batas kepercayaan (trust boundary) dan gerbang persetujuan

```mermaid
flowchart LR
    subgraph AGEN["Zona agen — folder D:\\Agent 2 (WorkBuddy)"]
        D["keluar/draf/SPJ-xxxx/<br/>berkas draf"]
        T["Tool MCP<br/>ajukan_spj"]
    end
    subgraph BE["Zona eksekusi — backend (FastAPI + SQLite)"]
        M["Hitung sidik SHA-256<br/>semua berkas draf"]
        G{"Sidik masih sama<br/>saat disetujui?"}
        C["Salin byte-per-byte<br/>+ verifikasi ulang"]
        L[("Log audit<br/>hash berantai")]
    end
    subgraph MP["Meja Pimpinan (Next.js)"]
        B["Bendahara:<br/>Setujui & cairkan / Tolak"]
    end
    S["siap-cair/<br/>(di luar folder agen)"]
    D --> T -->|"HTTP + bearer token"| M --> L
    M --> B
    B -->|Setujui| G
    G -->|ya| C --> S
    G -->|tidak| X["Ditolak:<br/>berkas berubah sejak diajukan"]
    C --> L
    X --> L
```

**Garis batas:** semua di zona agen hanya bisa *mengajukan*. Penulisan ke `siap-cair/` hanya dilakukan backend setelah klik bendahara, dan folder itu berada di luar folder yang diizinkan untuk WorkBuddy.

## 3. Komponen
| Komponen | Teknologi | Tanggung jawab |
|---|---|---|
| Tim agen | WorkBuddy Expert Team + 7 SKILL.md | Memahami, membaca, memverifikasi, mengaudit, menyusun |
| Data demo | Excel/JSON/TXT/PDF fiktif | Pegawai, SBM, SPT, libur, 11 kasus bukti |
| Konektor | MCP streamable HTTP, bearer token per akun | `ajukan_spj` (+ tool baca) |
| Backend | Python, FastAPI, FastMCP, SQLite, pytest (137 tes) | Gerbang SPJ, audit hash berantai, aturan deterministik |
| Meja Pimpinan | Next.js | Antarmuka konfirmasi bendahara, mobile-first |

## 4. Keputusan desain & trade-off
| Keputusan | Alasan | Konsekuensi |
|---|---|---|
| LLM untuk memahami, kode untuk menghitung & mengeksekusi | Angka dan aturan harus bisa diulang dan diuji; LLM bisa salah hitung | Butuh skrip hitung dan formula Excel |
| Pencairan di backend, bukan di agen | Pengujian membuktikan agen bisa menyimulasikan kerja, menyalin versi berbeda, dan menulis persetujuan palsu bila diberi akses | Perlu menjalankan backend + konektor MCP |
| Sidik versi seluruh berkas (manifest) | Persetujuan harus atas berkas yang persis sama | Revisi sekecil apa pun → ajukan ulang (versi baru) |
| Temuan asli tidak masuk loop perbaikan | Mencegah agen berputar 3 kali tanpa hasil | Temuan langsung tampil ke bendahara |
| Deteksi ganda lintas kasus hanya berupa sinyal | Menjaga izin: agen tidak melihat isi kasus pegawai lain | Bendahara yang menelusuri pasangannya |
| Data dan aturan SBM fiktif & disederhanakan | Panitia mengizinkan data dummy; menghindari klaim regulasi yang belum diverifikasi | Perlu diganti SBM resmi saat implementasi nyata |
