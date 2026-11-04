"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, type Kasus, type SPJ } from "@/lib/api";
import { waktuLokal } from "@/lib/format";
import { rupiah } from "@/lib/rupiah";

const URUT_RISIKO = { tinggi: 0, normal: 1 } as const;

function Beranda() {
  const [spj, setSpj] = useState<SPJ[] | null>(null);
  const [kasus, setKasus] = useState<Kasus[]>([]);

  useEffect(() => {
    const muat = () => {
      api<SPJ[]>("/spj").then(setSpj).catch(() => {});
      api<Kasus[]>("/kasus").then(setKasus).catch(() => {});
    };
    muat();
    const t = setInterval(muat, 15000);
    return () => clearInterval(t);
  }, []);

  if (spj === null) return <p className="info" role="status" style={{ marginTop: 24 }}>Memuat…</p>;

  const menunggu = spj
    .filter((s) => s.status === "PENDING")
    .sort((a, b) => URUT_RISIKO[a.risiko] - URUT_RISIKO[b.risiko] || b.diajukan.localeCompare(a.diajukan));
  const khusus = menunggu.filter((s) => s.risiko === "tinggi");
  const cair = spj.filter((s) => s.status === "DICAIRKAN");
  const diputuskan = spj.filter((s) => s.status !== "PENDING").slice(0, 5);
  const diperiksa = kasus.filter((k) => k.status === "DIPERIKSA_AGEN" || k.status === "DITERIMA");
  const jumlah = (xs: SPJ[]) => xs.reduce((n, s) => n + s.total_dibayar, 0);

  return (
    <>
      <div className="judul-dasbor">
        <div>
          <h1 className="judul-halaman">Beranda</h1>
          <p className="sub-halaman">Ringkasan SPJ perjalanan dinas yang perlu keputusan Bendahara Pengeluaran.</p>
        </div>
        <Link className="tombol tombol-utama" href="/spj">Tinjau SPJ</Link>
      </div>

      <section className="ringkasan" aria-label="Ringkasan">
        <Link href="/spj" className="ringkas">
          <span className="ringkas-label">Menunggu keputusan</span>
          <span className="ringkas-angka">{menunggu.length}</span>
          <span className="ringkas-ket">senilai {rupiah(jumlah(menunggu))}</span>
        </Link>
        <Link href="/spj" className="ringkas" data-nada={khusus.length ? "bahaya" : undefined}>
          <span className="ringkas-label">Perlu persetujuan khusus</span>
          <span className="ringkas-angka">{khusus.length}</span>
          <span className="ringkas-ket">ada catatan penting atau di atas Rp10 juta</span>
        </Link>
        <Link href="/proses" className="ringkas">
          <span className="ringkas-label">Sedang diperiksa</span>
          <span className="ringkas-angka">{diperiksa.length}</span>
          <span className="ringkas-ket">pengajuan yang belum selesai diperiksa</span>
        </Link>
        <div className="ringkas" data-nada="aman">
          <span className="ringkas-label">Disetujui untuk dibayar</span>
          <span className="ringkas-angka">{cair.length}</span>
          <span className="ringkas-ket">senilai {rupiah(jumlah(cair))}</span>
        </div>
      </section>

      <section className="panel" aria-labelledby="judul-menunggu">
        <div className="panel-kepala">
          <h2 id="judul-menunggu">SPJ menunggu keputusan</h2>
          <Link href="/spj">Lihat semua</Link>
        </div>
        {menunggu.length === 0 ? (
          <p className="panel-kosong">Tidak ada SPJ yang menunggu keputusan.</p>
        ) : (
          <div className="tabel-gulir">
            <table className="tabel">
              <thead>
                <tr>
                  <th>Nomor</th>
                  <th>Pegawai</th>
                  <th>Tujuan</th>
                  <th className="r">Layak dibayar</th>
                  <th>Catatan</th>
                  <th>Masuk</th>
                  <th><span className="sr-only">Aksi</span></th>
                </tr>
              </thead>
              <tbody>
                {menunggu.map((s) => {
                  const penting = s.temuan.filter((t) => t.level === "KRITIS").length;
                  return (
                    <tr key={s.nomor}>
                      <td className="nomor">{s.nomor}</td>
                      <td>{s.pegawai}</td>
                      <td>{s.tujuan}</td>
                      <td className="r">{rupiah(s.total_dibayar)}</td>
                      <td>
                        {s.risiko === "tinggi" ? (
                          <span className="lencana bahaya">{penting ? `${penting} sangat penting` : "Persetujuan khusus"}</span>
                        ) : (
                          <span className="lencana">{s.temuan.length ? `${s.temuan.length} catatan` : "Sesuai"}</span>
                        )}
                      </td>
                      <td className="redup">{waktuLokal(s.diajukan)}</td>
                      <td className="r"><Link href={`/spj/${s.nomor}`}>Buka</Link></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {diputuskan.length > 0 && (
        <section className="panel" aria-labelledby="judul-terakhir">
          <div className="panel-kepala">
            <h2 id="judul-terakhir">Keputusan terakhir</h2>
            <Link href="/audit">Jejak audit</Link>
          </div>
          <div className="tabel-gulir">
            <table className="tabel">
              <thead>
                <tr><th>Nomor</th><th>Pegawai</th><th className="r">Layak dibayar</th><th>Status</th><th>Oleh</th></tr>
              </thead>
              <tbody>
                {diputuskan.map((s) => (
                  <tr key={s.nomor}>
                    <td className="nomor"><Link href={`/spj/${s.nomor}`}>{s.nomor}</Link></td>
                    <td>{s.pegawai}</td>
                    <td className="r">{rupiah(s.total_dibayar)}</td>
                    <td>
                      <span className={`lencana ${s.status === "DICAIRKAN" ? "aman" : "bahaya"}`}>
                        {s.status === "DICAIRKAN" ? "Disetujui" : "Ditolak"}
                      </span>
                    </td>
                    <td className="redup">{s.diputuskan_oleh ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <Beranda />
    </Shell>
  );
}
