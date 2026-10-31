"use client";

import DaftarKasus from "@/components/DaftarKasus";
import Shell from "@/components/Shell";

export default function Page() {
  return (
    <Shell>
      <h1 className="judul-halaman">Proses tim agen</h1>
      <p className="sub-halaman">Pengajuan pegawai dan apa yang sedang dikerjakan tiap agen. Pilih salah satu untuk melihat prosesnya.</p>
      <DaftarKasus
        kosong={
          <>
            <h2>Belum ada aktivitas</h2>
            <p>Jalankan skrip jembatan di laptop WorkBuddy supaya progres agen terkirim ke sini.</p>
          </>
        }
      />
    </Shell>
  );
}
