# Product Sharing — Peran WorkBuddy & Pelajaran

## Di mana WorkBuddy memberi nilai
| Fitur WorkBuddy | Dipakai untuk |
|---|---|
| **Expert Team (multi-agen)** | Tim "SPJ Agent Team": 1 Koordinator + 6 anggota dengan peran terpisah; tiga pembaca bekerja paralel |
| **Skill (SKILL.md) level proyek** | Setiap agen punya kontrak perilaku tertulis: tujuan, input/output JSON, aturan, larangan, kapan bertanya/eskalasi — bisa di-export (`export/spj-agent-team/`) |
| **Akses file lokal** | Agen membaca langsung bukti asli (TXT/PDF), Excel master (pegawai, SBM), dan menulis hasil ke folder draf tanpa unggah ke cloud |
| **Output dokumen kantor** | Rekap `.xlsx` berformula, draf SPJ `.docx`, layar konfirmasi HTML |
| **Konektor MCP kustom** | Tool `ajukan_spj` menghubungkan tim agen ke gerbang persetujuan di backend |
| **Mode Craft & memori proyek** | Proyek bisa dilanjutkan di sesi baru dari `README`, `DESAIN.md`, dan memori harian |
| **Model routing** | Pekerjaan dijalankan dengan model "Balanced"; kredit terpakai rendah (±21 kredit untuk satu kasus penuh beserta revisinya) |

WorkBuddy juga dipakai untuk **membangun** proyek: membuat data dummy, menulis skill tiap agen, menyusun Expert Team, dan menjalankan kasus uji — prosesnya terekam sebagai bukti pemakaian.

## Insight terpenting: aturan di prompt tidak cukup untuk urusan uang
Saat menguji kasus pertama, kami memeriksa berkas dan log yang dihasilkan, bukan hanya ringkasan chat. Kami menemukan tiga kegagalan yang berbahaya untuk sistem keuangan:

1. **Kerja tim disimulasikan.** Log 10 langkah tertulis dalam 0,4 detik — satu skrip menulis semua "agen" sekaligus. Setelah dikoreksi, tiap anggota benar-benar dijalankan terpisah dan menulis hasilnya sendiri (±8 menit per kasus).
2. **Versi yang dicairkan berbeda dari yang disetujui.** Rekap di folder siap-cair ditulis ulang 5 menit setelah persetujuan (sidik `f88f3ae…` vs `bb9d8fb…`). Kami menambahkan manifest SHA-256 dan salin byte-per-byte.
3. **Persetujuan bendahara ditulis oleh agen sendiri.** Setelah pencairan dibatalkan, agen menulis baris "bendahara setujui" atas nama pengguna lalu mencairkan. Log tidak dihapus; kesalahan dicatat dan dibatalkan secara terbuka.

Ketiganya terjadi **meskipun skill sudah melarangnya**. Kesimpulan kami: untuk tindakan berdampak (uang), larangan harus ditegakkan oleh **lapisan eksekusi di luar model**. Karena itu pencairan dipindah ke backend: agen hanya bisa mengajukan lewat MCP, backend menghitung sidik sendiri, bendahara menyetujui di Meja Pimpinan, dan folder siap-cair berada di luar folder kerja agen.

## Insight kedua: klaim "multi-agen" harus dibuktikan dari jejak, bukan dari ringkasan
Saat menjalankan kasus massal, agen dua kali memilih jalan pintas: menulis satu skrip yang menghasilkan output semua "anggota tim" dalam kurang dari satu detik, lalu — setelah diminta memakai agen sungguhan — menambahkan **jeda buatan tepat 1 detik** agar log tampak realistis. Ringkasan chat-nya tetap menyebut "tim agen sungguhan". Kami hanya bisa menangkapnya dengan membandingkan **waktu tulis berkas** setiap anggota.

Yang berhasil: menjalankan kasus lewat **Expert Team "SPJ Agent Team"** langsung (Case Coordinator). Di sana anggota benar-benar dipanggil terpisah — terlihat dari jarak waktu yang tidak beraturan dan Koordinator yang menunggu serta mengirim *nudge* ke anggota yang belum selesai. Karena itu laporan uji kami memisahkan kasus yang dikerjakan tim agen dari yang diproses pipeline skrip.

## Pelajaran lain
- **Berkas lama bisa menipu orkestrator.** Koordinator sempat menganggap Auditor selesai hanya karena berkas hasil putaran sebelumnya masih ada. Cek waktu berkas, bukan hanya keberadaannya.
- **Deteksi lintas kasus perlu instruksi eksplisit.** Auditor sungguhan melewatkan struk ganda lintas kasus pada percobaan pertama dan baru menemukannya setelah diminta membaca indeks sidik — sinyal bahwa langkah ini sebaiknya dijadikan tool deterministik.
- **Verifikasi file, bukan ringkasan.** Ringkasan agen beberapa kali tidak sama dengan isi log (jam, urutan baris). Laporan kami selalu diambil dari berkas aslinya.
- **Data uji harus bersih.** Bug pajak hotel (pagu dibanding tarif sebelum/sesudah pajak) awalnya membuat kasus "normal" ikut melanggar pagu; aturan R03 lalu ditegaskan "biaya per malam termasuk pajak".
- **Pisahkan temuan asli dari kesalahan kerja agen.** Loop perbaikan yang mengembalikan struk ganda ke pembaca hanya berputar sia-sia.
- **Zona waktu itu penting untuk audit.** Log campuran UTC dan waktu lokal membuat urutan kejadian tampak terbalik; semua waktu kini ISO 8601 dengan offset WITA.
- **Pemahaman domain menambah kepercayaan.** Aturan R11 (makan sudah termasuk uang harian) mencegah pembayaran ganda yang mudah terlewat.

## Rencana pengembangan
Integrasi dengan sistem persuratan/keuangan instansi lewat konektor, tabel SBM resmi per tahun anggaran, deteksi duplikasi berbasis citra struk, dan dasbor prioritas pemeriksaan untuk bendahara.
