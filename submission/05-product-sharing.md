# Product Sharing — Peran WorkBuddy & Pelajaran

## Di mana WorkBuddy memberi nilai
| Fitur WorkBuddy | Dipakai untuk |
|---|---|
| **Expert Team (multi-agen)** | Tim "SPJ Agent Team": 1 Koordinator + 6 anggota dengan peran terpisah; tiga pembaca bekerja paralel |
| **Skill (SKILL.md) level proyek** | Setiap agen punya kontrak perilaku tertulis: tujuan, input/output JSON, aturan, larangan, kapan bertanya/eskalasi — bisa di-export (`export/spj-agent-team/`) |
| **Akses file lokal** | Agen membaca langsung bukti asli (TXT/PDF), Excel master (pegawai, SBM), dan menulis hasil ke folder draf tanpa unggah ke cloud |
| **Output dokumen kantor** | Rekap `.xlsx` berformula, draf SPJ `.docx`, layar konfirmasi HTML |
| **Konektor MCP kustom** | Tool `periksa_aturan` (kalkulator aturan) dan `ajukan_spj` (gerbang persetujuan) di backend; dipasang lewat Connectors → Custom connectors |
| **Mode Craft & memori proyek** | Proyek bisa dilanjutkan di sesi baru dari `README`, `DESAIN.md`, dan memori harian |
| **Model routing** | Pekerjaan dijalankan dengan model "Balanced"; kredit terpakai rendah (±21 kredit untuk satu kasus penuh beserta revisinya) |
| **Pemulihan anggota gagal** | Saat satu Auditor gagal karena gangguan jaringan, Koordinator mengulang dengan agen baru tanpa meninggalkan berkas setengah jadi |

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

## Insight ketiga: pisahkan "menilai" dari "menghitung"
Di putaran awal, model menghitung sendiri pagu hotel, malam di luar masa tugas, dan batas Rp10 juta. Hasilnya lambat (17–25 menit per kasus) dan dua kasus gagal karena aturan terlewat. Kami memindahkan semua hitungan ke tool `periksa_aturan` di backend, dan pembuatan dokumen ke skrip templat. Agen tetap membaca bukti, menilai, bertanya, dan memeriksa ulang.

Hasilnya: satu kasus kini 4–9 menit, kasus yang dulu gagal (libur nasional, total di atas Rp10 juta) terdeteksi otomatis, dan backend bisa membandingkan angka yang diajukan agen dengan hasil kalkulator.

## Insight keempat: agen yang mengawasi bisa menemukan kesalahan pengawasnya
Saat batch terakhir, Auditor menemukan dua celah di kalkulator kami sendiri: struk ganda tidak memicu persetujuan khusus, dan nominal buram lolos sebagai "Sesuai" karena Pemeriksa Batas Biaya mengubah nilai kosong menjadi nol. Auditor tidak mengubah angka diam-diam. Ia menambah temuan berlabel `AUDITOR`, dan kami memperbaiki kalkulatornya. Kombinasi kode yang tegas dan agen pemeriksa yang kritis ternyata lebih kuat daripada salah satunya.

## Pelajaran tambahan dari minggu terakhir
- **Agen menulis angka dari ingatan.** Koordinator dua kali menulis kode sidik berkas dari ingatan, lalu mengoreksi sendiri dari balasan tool. Ini tidak berbahaya karena backend menghitung sidiknya sendiri, tapi menegaskan bahwa nilai penting tidak boleh dipercayakan pada ingatan model.
- **Jam di log bisa dikarang.** Baris log sempat tercatat lebih awal dari kejadian sebenarnya. Sekarang jam diisi alat dari jam komputer, dan klaim jam dari agen disimpan terpisah.
- **Rantai hash benar-benar menangkap perubahan.** Pemeriksa log menemukan baris yang ditulis skrip dengan hash tidak cocok. Baris itu dibiarkan sebagai bukti dan dikoreksi lewat baris baru, bukan ditulis ulang.
- **Instruksi Expert Team ada di dua tempat.** Mengubah `skills/` saja tidak berpengaruh; tim membaca instruksi di berkas agen plugin. Pelajaran ini menghemat banyak waktu begitu ditemukan.
- **AI tidak bisa memeriksa berkas fisik.** SPPD bercap, bukti asli, dan meterai tetap tugas bendahara. Kami menjadikannya daftar periksa wajib, bukan menyembunyikan batasannya.

## Rencana pengembangan
Mode periksa cepat (target di bawah 90 detik) untuk Demo Day; aturan kelas kabin dan pagu tiket; Daftar Pengeluaran Riil dan pola uang muka (panjar); tabel SBM resmi per tahun anggaran; deteksi duplikasi berbasis citra struk; integrasi dengan sistem keuangan instansi.
