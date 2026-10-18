"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, type Rencana } from "@/lib/api";
import { JENIS_AKSI, SIFAT, waktuLokal } from "@/lib/format";

function Antrean() {
  const [daftar, setDaftar] = useState<Rencana[] | null>(null);

  useEffect(() => {
    const muat = () => api<Rencana[]>("/rencana?status=PENDING").then(setDaftar).catch(() => {});
    muat();
    const t = setInterval(muat, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <h1 className="judul-halaman">Menunggu keputusan</h1>
      <p className="sub-halaman">Tidak ada yang dikirim sebelum Anda menyetujuinya.</p>
      {daftar === null ? (
        <p className="info" role="status">Memuat antrean…</p>
      ) : daftar.length === 0 ? (
        <div className="kosong">
          <h2>Meja bersih</h2>
          <p>Rencana baru muncul di sini setelah agent di WorkBuddy membaca surat atau pesan dan mengajukannya.</p>
        </div>
      ) : (
        <ul className="antrean">
          {daftar.map((r) => (
            <li key={r.id}>
              <Link className="kartu" href={`/rencana/${r.id}`} data-sifat={r.surat.sifat}>
                <div className="kartu-atas">
                  <span>{r.surat.pengirim ?? "Pengirim tidak disebut"}</span>
                  <span>{waktuLokal(r.dibuat)}</span>
                </div>
                <h2>{r.surat.perihal ?? r.surat.ringkasan}</h2>
                <p>{r.surat.ringkasan}</p>
                <div className="lencana-baris">
                  {r.surat.sifat !== "biasa" && (
                    <span className={`lencana ${r.surat.sifat === "rahasia" ? "bahaya" : "stempel"}`}>{SIFAT[r.surat.sifat]}</span>
                  )}
                  {r.risiko === "tinggi" && <span className="lencana bahaya">Risiko tinggi</span>}
                  {r.peringatan.length > 0 && <span className="lencana bahaya">⚠ {r.peringatan.length} peringatan</span>}
                  <span className="lencana">{r.aksi.map((a) => JENIS_AKSI[a.jenis]).join(" · ")}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <Antrean />
    </Shell>
  );
}
