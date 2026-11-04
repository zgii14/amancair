# Design — Meja Pimpinan (AmanCair)

Sistem tampilan yang dikunci untuk semua halaman Meja Pimpinan. Halaman baru mengikuti berkas ini; jangan memilih warna atau huruf sendiri per halaman.

## Pengguna dan nada
- Pengguna: bendahara, pegawai, dan pimpinan dinas. Bukan orang IT.
- Nada: utilitarian, gaya aplikasi instansi pemerintah. Bersih, tenang, mudah dibaca.
- Bukan: gradien, kilau, ikon robot, emoji, pil berdenyut, stempel miring.

## Warna (token di `app/globals.css` `:root`)
| Token | Nilai | Pakai untuk |
|---|---|---|
| `--meja` | `#F4F7FB` | Latar halaman |
| `--kertas` | `#FFFFFF` | Kartu, lembar, tabel |
| `--tinta` | `#0F2547` | Teks utama (navy) |
| `--tinta-pudar` | `#55657E` | Teks keterangan |
| `--stempel` | `#1A56B8` | Aksen biru: tombol utama, tautan, tab aktif |
| `--stempel-gelap` | `#14458F` | Hover tombol utama |
| `--stempel-muda` | `#E8F0FC` | Latar label biru, baris aktif |
| `--garis` | `#D3DCE8` | Garis tepi |
| `--garis-tipis` | `#E7ECF3` | Garis dalam tabel |
| `--merah` / `--merah-muda` | `#B42318` / `#FDECEA` | Ditahan, ditolak, risiko tinggi |
| `--hijau` / `--hijau-muda` | `#1E6B45` / `#E6F4EC` | Dicairkan, selesai |
| `--kuning` / `--kuning-muda` | `#8A5A00` / `#FFF4D6` | Perlu dicek |

Biru dipakai hemat: tombol utama, tautan, tab aktif. Merah dan hijau hanya untuk status.

## Huruf
- Semua teks: Public Sans (400 isi, 600 label, 700 judul). Tanpa huruf miring di judul.
- Angka uang dan nomor: `font-variant-numeric: tabular-nums`.
- Kode/sidik: IBM Plex Mono, ukuran kecil, hanya di bagian teknis (sidik berkas).

## Komponen
- Kepala: putih, garis biru 4px di atas, tab navigasi bergaris bawah biru saat aktif.
- Kartu: putih, garis 1px, sudut 8px, tanpa garis warna di sisi.
- Label status: kotak kecil sudut 4px, teks 12px tebal, warna sesuai status.
- Tombol utama: biru penuh; tombol kedua: putih bergaris; tombol bahaya: putih bergaris merah.
- Status keputusan (Dicairkan/Ditolak): kotak lurus di pojok lembar, tidak miring, tanpa animasi.
- Papan proses: daftar tahapan bernomor; tahap aktif bergaris biru dengan putaran kecil, selesai bertanda centang hijau.

## Gerak
- Hanya transisi warna 150 ms dan putaran kecil penanda proses.
- `prefers-reduced-motion: reduce` mematikan semua animasi.
