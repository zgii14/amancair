"use client";

import DaftarKasus from "@/components/DaftarKasus";
import Shell from "@/components/Shell";

export default function Page() {
  return (
    <Shell>
      <h1 className="judul-halaman">Proses pemeriksaan</h1>
      <p className="sub-halaman">Pengajuan pegawai dan tahap pemeriksaannya. Pilih salah satu untuk melihat rinciannya.</p>
      <DaftarKasus
        kosong={
          <>
            <h2>Belum ada aktivitas</h2>
            <p>Pengajuan yang sedang diperiksa akan tampil di sini.</p>
          </>
        }
      />
    </Shell>
  );
}
