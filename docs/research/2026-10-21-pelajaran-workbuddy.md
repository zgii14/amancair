# Pelajaran WorkBuddy (bahan belajar tim)

Tanggal: 2026-10-21 · Sumber utama: ulasan blog Eigent (pesaing WorkBuddy, 19 Jun 2026) + riset 18 Okt.
⚠️ Sebagian klaim (daftar integrasi, harga) dari pihak ketiga — verifikasi di aplikasi saat spike.

## Inti
1. **Agen, bukan chatbot** — beri tujuan → WorkBuddy membuat rencana, memanggil alat, menyerahkan hasil jadi (laporan, spreadsheet, dokumen).
2. **Multi-agent / Expert Team** — permintaan dipecah jadi sub-tugas untuk agen khusus, bisa paralel.
3. **Akses file lokal (desktop)** — membaca/mengolah PDF, Excel, folder di laptop tanpa upload.
4. **Input multimodal** — gabungan PDF + spreadsheet + URL dalam satu tugas.
5. **Konektor/MCP + Skill** — alat modular yang bisa ditambah; skill = resep kerja yang disimpan dan dipakai ulang; bisa routing ke beberapa model (Hunyuan, DeepSeek, GLM, Kimi, MiniMax).
6. **Perintah jarak jauh** — tugas dikirim lewat Telegram/Slack/Discord/WeCom/Feishu/DingTalk/QQ, hasil dilaporkan balik.
7. **Posisi: lapisan koordinasi di atas alat yang sudah ada**, bukan pengganti.
8. **Kelemahan yang diakui: output wajib ditinjau manusia sebelum dikirim**; konfigurasi alat kustom/MCP butuh kemampuan teknis; dokumentasi condong ke pasar Tiongkok.

## Kekuatan yang cocok untuk Agent Disposisi
| Kekuatan | Pemakaian |
|---|---|
| File lokal | Folder `Surat Masuk/` (scan PDF) dibaca langsung oleh Pembaca |
| Hasil dokumen jadi | Draf surat balasan .docx format dinas; rekap disposisi .xlsx |
| Perintah dari HP | Voice note Pak Camat via Telegram → diproses WorkBuddy; approval tetap di Meja Pimpinan |
| Expert Team | Pembaca → Penyusun → Pemeriksa, serah-terima terlihat di demo |
| Posisi "lapisan di atas" | Sama dengan positioning: asisten di atas SRIKANDI |
| Output wajib ditinjau | Masalah yang kita jawab dengan approval gate + audit |
