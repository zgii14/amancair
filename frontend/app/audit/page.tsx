"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { useSesi } from "@/components/Shell";
import { api, type CatatanAudit } from "@/lib/api";
import { waktuLokal } from "@/lib/format";
import { rupiah } from "@/lib/rupiah";

const KEJADIAN: Record<string, string> = {
  rencana_diajukan: "Agent mengajukan rencana",
  rencana_ditolak_aturan: "Rencana ditolak aturan kantor",
  rencana_disetujui: "Pimpinan menyetujui",
  rencana_ditolak: "Pimpinan menolak",
  token_ditolak: "Eksekusi ditolak: persetujuan tidak sah",
  aksi_dieksekusi: "Aksi dikirim",
  rencana_dibatalkan: "Pengiriman dibatalkan",
  kasus_diajukan: "Pegawai mengajukan SPJ",
  spj_diperiksa_aturan: "Biaya dihitung sesuai aturan",
  spj_diajukan: "SPJ selesai diperiksa dan diajukan ke bendahara",
  spj_dicairkan: "Bendahara menyetujui untuk dibayar",
  spj_ditolak: "Bendahara menolak SPJ",
  spj_pencairan_ditolak: "Persetujuan ditolak sistem karena berkas berubah",
};

function Rincian({ c }: { c: CatatanAudit }) {
  const p = c.payload as Record<string, unknown>;
  const bagian: React.ReactNode[] = [];
  if (typeof p.rencana_id === "string") bagian.push(<Link key="r" href={`/rencana/${p.rencana_id}`}>Lihat rencana</Link>);
  if (typeof p.nomor === "string") bagian.push(<Link key="n" href={`/spj/${p.nomor}`}>{p.nomor}</Link>);
  if (typeof p.kasus === "string") bagian.push(<span key="k">Pengajuan {p.kasus.replace("kasus-", "no. ")}</span>);
  if (typeof p.total_dibayar === "number") bagian.push(<span key="t">Layak dibayar {rupiah(p.total_dibayar)}</span>);
  if (typeof p.versi === "number" && p.versi > 1) bagian.push(<span key="v">Revisi ke-{p.versi - 1}</span>);
  if (typeof p.alasan === "string") bagian.push(<span key="a">Alasan: {p.alasan}</span>);
  if (Array.isArray(p.pelanggaran)) {
    bagian.push(<span key="p">{(p.pelanggaran as { pesan: string }[]).map((x) => x.pesan).join(" ")}</span>);
  }
  if (typeof p.jenis === "string") bagian.push(<span key="j">Jenis: {p.jenis}</span>);
  return bagian.length ? <span className="info" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{bagian}</span> : null;
}

function Audit() {
  const { kontak } = useSesi();
  const [catatan, setCatatan] = useState<CatatanAudit[] | null>(null);
  const [rantai, setRantai] = useState<{ valid: boolean; seq_rusak: number | null } | null>(null);

  useEffect(() => {
    api<CatatanAudit[]>("/audit").then(setCatatan).catch(() => {});
    api<{ valid: boolean; seq_rusak: number | null }>("/audit/verifikasi").then(setRantai).catch(() => {});
  }, []);

  const aktor = (a: string) => (a === "executor" ? "Sistem eksekusi" : kontak(a)?.nama ?? a);

  return (
    <>
      <h1 className="judul-halaman">Jejak audit</h1>
      <p className="sub-halaman">Semua yang diajukan, diputuskan, dan dikirim. Tiap catatan dikunci ke catatan sebelumnya.</p>
      {rantai && (
        <div className="rantai" data-utuh={rantai.valid ? "ya" : "tidak"} role="status">
          {rantai.valid
            ? `Catatan utuh: ${catatan?.length ?? 0} catatan, tidak ada yang diubah atau dihapus.`
            : `Ada catatan yang diubah atau dihapus, mulai catatan #${rantai.seq_rusak}.`}
        </div>
      )}
      {catatan === null ? (
        <p className="info" role="status">Memuat…</p>
      ) : (
        <ol className="daftar" reversed>
          {catatan.map((c) => (
            <li key={c.seq}>
              <div className="baris-atas">
                <span>#{c.seq} · {waktuLokal(c.waktu)}</span>
                <span>{aktor(c.aktor)}</span>
              </div>
              <span className="utama">{KEJADIAN[c.kejadian] ?? c.kejadian}</span>
              <Rincian c={c} />
              <code title="Kode pengaman catatan">{c.hash.slice(0, 16)}</code>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <Audit />
    </Shell>
  );
}
