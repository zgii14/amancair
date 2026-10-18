"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { useSesi } from "@/components/Shell";
import { api, type Rencana, type Terkirim } from "@/lib/api";
import { JENIS_AKSI, waktuLokal } from "@/lib/format";

const STATUS: Record<string, { label: string; kelas: string }> = {
  DISETUJUI: { label: "Disetujui", kelas: "stempel" },
  DIEKSEKUSI: { label: "Terkirim", kelas: "aman" },
  DITOLAK: { label: "Ditolak", kelas: "bahaya" },
  DIBATALKAN: { label: "Dibatalkan", kelas: "" },
};

function Riwayat() {
  const { kontak } = useSesi();
  const [rencana, setRencana] = useState<Rencana[] | null>(null);
  const [terkirim, setTerkirim] = useState<Terkirim[]>([]);

  useEffect(() => {
    api<Rencana[]>("/rencana").then((d) => setRencana(d.filter((r) => r.status !== "PENDING"))).catch(() => {});
    api<Terkirim[]>("/terkirim").then(setTerkirim).catch(() => {});
  }, []);

  const nama = (v: string) => kontak(v)?.nama ?? v;

  return (
    <>
      <h1 className="judul-halaman">Riwayat keputusan</h1>
      <p className="sub-halaman">Rencana yang sudah Anda putuskan dan apa saja yang benar-benar terkirim.</p>
      {rencana === null ? (
        <p className="info" role="status">Memuat…</p>
      ) : rencana.length === 0 ? (
        <div className="kosong"><h2>Belum ada keputusan</h2><p>Keputusan dari <Link href="/">antrean</Link> akan tercatat di sini.</p></div>
      ) : (
        <ul className="daftar">
          {rencana.map((r) => (
            <li key={r.id}>
              <div className="baris-atas">
                <span>{waktuLokal(r.dibuat)}</span>
                <span className={`lencana ${STATUS[r.status].kelas}`}>{STATUS[r.status].label}</span>
              </div>
              <Link className="utama" href={`/rencana/${r.id}`}>{r.surat.perihal ?? r.surat.ringkasan}</Link>
            </li>
          ))}
        </ul>
      )}

      <h2 className="subjudul">Terkirim</h2>
      {terkirim.length === 0 ? (
        <p className="info">Belum ada aksi yang terkirim. Aksi dikirim 60 detik setelah disetujui.</p>
      ) : (
        <ul className="daftar">
          {terkirim.map((t) => (
            <li key={t.id}>
              <div className="baris-atas">
                <span>{JENIS_AKSI[t.jenis]}</span>
                <span>{waktuLokal(t.waktu)}</span>
              </div>
              <span className="utama">{t.payload.judul}</span>
              <span className="info">Kepada: {t.payload.penerima.map((p) => nama(p.nilai)).join(", ")}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="info" style={{ marginTop: 10 }}>Pengiriman di demo ini memakai email, kalender, dan registri disposisi tiruan.</p>
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <Riwayat />
    </Shell>
  );
}
