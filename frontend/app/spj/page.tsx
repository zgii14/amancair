"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, type SPJ } from "@/lib/api";
import { waktuLokal } from "@/lib/format";
import { rupiah } from "@/lib/rupiah";

const STATUS: Record<string, { label: string; kelas: string }> = {
  PENDING: { label: "Menunggu", kelas: "stempel" },
  DICAIRKAN: { label: "Dicairkan", kelas: "aman" },
  DITOLAK: { label: "Ditolak", kelas: "bahaya" },
};

function DaftarSPJ() {
  const [daftar, setDaftar] = useState<SPJ[] | null>(null);

  useEffect(() => {
    const muat = () => api<SPJ[]>("/spj").then(setDaftar).catch(() => {});
    muat();
    const t = setInterval(muat, 10000);
    return () => clearInterval(t);
  }, []);

  const menunggu = daftar?.filter((s) => s.status === "PENDING") ?? [];
  const selesai = daftar?.filter((s) => s.status !== "PENDING") ?? [];

  return (
    <>
      <h1 className="judul-halaman">SPJ menunggu keputusan</h1>
      <p className="sub-halaman">Disusun tim agen di WorkBuddy. Tidak ada yang dicairkan sebelum Anda menyetujuinya di sini.</p>
      {daftar === null ? (
        <p className="info" role="status">Memuat…</p>
      ) : menunggu.length === 0 ? (
        <div className="kosong">
          <h2>Tidak ada SPJ menunggu</h2>
          <p>SPJ muncul di sini setelah tim agen menyelesaikan pemeriksaan dan mengajukannya.</p>
        </div>
      ) : (
        <ul className="antrean">
          {menunggu.map((s) => {
            const kritis = s.temuan.filter((t) => t.level === "KRITIS").length;
            return (
              <li key={s.nomor}>
                <Link className="kartu" href={`/spj/${s.nomor}`} data-sifat={s.risiko === "tinggi" ? "rahasia" : "biasa"}>
                  <div className="kartu-atas">
                    <span>{s.nomor} · versi {s.versi}</span>
                    <span>{waktuLokal(s.diajukan)}</span>
                  </div>
                  <h2>{s.pegawai} — {s.tujuan}</h2>
                  <p>Diajukan {rupiah(s.total_diajukan)} · dibayar {rupiah(s.total_dibayar)}</p>
                  <div className="lencana-baris">
                    {kritis > 0 && <span className="lencana bahaya">{kritis} sangat penting</span>}
                    {s.risiko === "tinggi" && <span className="lencana bahaya">Perlu persetujuan khusus</span>}
                    {s.perintah_tersisip.length > 0 && <span className="lencana bahaya">Ada tulisan perintah di bukti</span>}
                    <span className="lencana">{s.temuan.length} catatan</span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      {selesai.length > 0 && (
        <>
          <h2 className="subjudul">Sudah diputuskan</h2>
          <ul className="daftar">
            {selesai.map((s) => (
              <li key={s.nomor}>
                <div className="baris-atas">
                  <span>{s.nomor}</span>
                  <span className={`lencana ${STATUS[s.status].kelas}`}>{STATUS[s.status].label}</span>
                </div>
                <Link className="utama" href={`/spj/${s.nomor}`}>{s.pegawai} — {s.tujuan}</Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <DaftarSPJ />
    </Shell>
  );
}
