"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LABEL_STATUS } from "@/components/LangkahStatus";
import { agenAktif, api, type Kasus } from "@/lib/api";
import { rupiah } from "@/lib/rupiah";

const KELAS: Record<string, string> = {
  DITERIMA: "",
  DIPERIKSA_AGEN: "stempel",
  MENUNGGU_BENDAHARA: "stempel",
  DICAIRKAN: "aman",
  DITOLAK: "bahaya",
};

export default function DaftarKasus({ kosong }: { kosong: React.ReactNode }) {
  const [daftar, setDaftar] = useState<Kasus[] | null>(null);

  useEffect(() => {
    const muat = () => api<Kasus[]>("/kasus").then(setDaftar).catch(() => {});
    muat();
    const t = setInterval(muat, 4000);
    return () => clearInterval(t);
  }, []);

  if (daftar === null) return <p className="info" role="status">Memuat…</p>;
  if (daftar.length === 0) return <div className="kosong">{kosong}</div>;

  return (
    <ul className="antrean">
      {daftar.map((k) => (
        <li key={k.id}>
          <Link className="kartu" href={`/proses/${k.id}`}>
            <div className="kartu-atas">
              <span>{k.nomor_spj}</span>
              <span className={`lencana ${KELAS[k.status]}`}>
                {agenAktif(k) && <i className="denyut" aria-hidden="true" />}
                {LABEL_STATUS[k.status]}
              </span>
            </div>
            <h2>{k.nama_pegawai ?? "Kasus uji proyek WorkBuddy"}{k.tujuan ? ` — ${k.tujuan}` : ""}</h2>
            <p>
              {k.spj
                ? `Diajukan ${rupiah(k.spj.total_diajukan)} · dibayar ${rupiah(k.spj.total_dibayar)} · ${k.spj.jumlah_temuan} temuan`
                : k.status === "DITERIMA"
                  ? "Menunggu diambil tim agen"
                  : `${k.jumlah_progres} aktivitas agen tercatat`}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
