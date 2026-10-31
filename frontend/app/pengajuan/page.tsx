"use client";

import Link from "next/link";
import DaftarKasus from "@/components/DaftarKasus";
import Shell from "@/components/Shell";

export default function Page() {
  return (
    <Shell>
      <h1 className="judul-halaman">SPJ saya</h1>
      <p className="sub-halaman">Pantau pengajuan Anda: kapan diperiksa tim agen, kapan diputuskan bendahara.</p>
      <p style={{ marginBottom: 16 }}>
        <Link className="tombol tombol-utama" href="/pengajuan/baru">+ Ajukan SPJ baru</Link>
      </p>
      <DaftarKasus
        kosong={
          <>
            <h2>Belum ada pengajuan</h2>
            <p>Setelah pulang dinas, unggah tiket, invoice hotel, dan struk Anda di sini.</p>
          </>
        }
      />
    </Shell>
  );
}
