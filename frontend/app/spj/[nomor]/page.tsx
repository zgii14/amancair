"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import Shell, { useSesi } from "@/components/Shell";
import { api, ApiError, post, type SPJ } from "@/lib/api";
import { waktuLokal } from "@/lib/format";
import { rupiah } from "@/lib/rupiah";

const CAP: Record<string, { teks: string; warna?: string; kecil: string }> = {
  DICAIRKAN: { teks: "Dicairkan", kecil: "salinan identik terverifikasi" },
  DITOLAK: { teks: "Ditolak", warna: "merah", kecil: "tidak dicairkan" },
};

const KELAS_LEVEL: Record<string, string> = { KRITIS: "bahaya", TINGGI: "bahaya", SEDANG: "stempel", RENDAH: "" };

function LembarSPJ() {
  const { nomor } = useParams<{ nomor: string }>();
  const { me, segarkanHitung } = useSesi();
  const [s, setS] = useState<SPJ | null>(null);
  const [tidakAda, setTidakAda] = useState(false);
  const [mode, setMode] = useState<"lihat" | "tolak">("lihat");
  const [alasan, setAlasan] = useState("");
  const [cek, setCek] = useState(false);
  const [galat, setGalat] = useState("");
  const [proses, setProses] = useState(false);
  const [capBaru, setCapBaru] = useState(false);

  const muat = useCallback(async () => {
    try {
      setS(await api<SPJ>(`/spj/${nomor}`));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setTidakAda(true);
    }
  }, [nomor]);

  useEffect(() => {
    muat();
  }, [muat]);

  async function putuskan(aksi: "setujui" | "tolak") {
    if (aksi === "tolak" && !alasan.trim()) {
      setGalat("Tulis alasan agar tim agen bisa memperbaiki dan mengajukan ulang.");
      return;
    }
    setProses(true);
    setGalat("");
    try {
      await post(`/spj/${nomor}/${aksi}`, aksi === "setujui" ? { konfirmasi_risiko: cek } : { alasan: alasan.trim() });
      setCapBaru(true);
      setMode("lihat");
      await muat();
      segarkanHitung();
    } catch (e) {
      setGalat(e instanceof ApiError ? e.message : "Permintaan gagal. Coba lagi.");
    } finally {
      setProses(false);
    }
  }

  if (tidakAda) {
    return (
      <div className="kosong" style={{ marginTop: 24 }}>
        <h2>SPJ tidak ditemukan</h2>
        <p><Link href="/spj">Kembali ke daftar SPJ</Link></p>
      </div>
    );
  }
  if (!s) return <p className="info" role="status" style={{ marginTop: 24 }}>Memuat SPJ…</p>;

  const cap = CAP[s.status];
  const tinggi = s.risiko === "tinggi";
  const bisaPutuskan = s.status === "PENDING" && me.boleh_menyetujui;
  const berkas = Object.keys(s.manifest);
  const url = (rel: string) => `/api/spj/${s.nomor}/berkas/${rel}`;

  return (
    <>
      <p style={{ marginTop: 16 }}><Link href="/spj">← Daftar SPJ</Link></p>
      <article className="lembar" aria-labelledby="judul-spj">
        {cap && (
          <div className="cap" data-warna={cap.warna} data-baru={capBaru ? "ya" : "tidak"} aria-hidden="true">
            {cap.teks}
            <small>{cap.kecil}</small>
          </div>
        )}
        <header className="kop">
          <div className="kop-label">Surat pertanggungjawaban · {s.nomor} · versi {s.versi}</div>
          <h1 id="judul-spj">{s.pegawai} — {s.tujuan}</h1>
          {cap && <p className="sr-only">Status: {cap.teks}</p>}
        </header>
        <dl className="kisi">
          <div className="kotak"><dt>Masa SPT</dt><dd>{s.tanggal_spt}</dd></div>
          <div className="kotak"><dt>Diajukan agen</dt><dd>{waktuLokal(s.diajukan)}</dd></div>
          <div className="kotak"><dt>Total diajukan</dt><dd>{rupiah(s.total_diajukan)}</dd></div>
          <div className="kotak"><dt>Akan dibayar</dt><dd>{rupiah(s.total_dibayar)}</dd></div>
        </dl>

        {s.perintah_tersisip.length > 0 && (
          <section className="peringatan" role="alert" aria-label="Perintah tersisip">
            <h2>Perintah tersisip di dokumen — diabaikan agen</h2>
            <ul>{s.perintah_tersisip.map((p) => <li key={p}>“{p}”</li>)}</ul>
          </section>
        )}

        <section className="bagian" aria-labelledby="temuan">
          <h2 id="temuan">Temuan ({s.temuan.length})</h2>
          {s.temuan.length === 0 ? (
            <p className="info">Tidak ada temuan. Semua bukti sesuai SPT dan SBM.</p>
          ) : (
            <ul className="daftar" style={{ border: 0 }}>
              {s.temuan.map((t, i) => (
                <li key={i}>
                  <div className="baris-atas">
                    <span className={`lencana ${KELAS_LEVEL[t.level]}`}>{t.level}</span>
                    <span>{t.aturan}</span>
                  </div>
                  <span>{t.deskripsi}</span>
                  {t.sumber && <code>Sumber: {t.sumber}</code>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bagian" aria-labelledby="berkas">
          <h2 id="berkas">Berkas yang disusun agen</h2>
          <p className="info" style={{ marginBottom: 8 }}>
            Periksa rincian per angka di rekap dan layar konfirmasi agen sebelum memutuskan.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {berkas.filter((b) => !b.startsWith("kerja/")).map((b) => (
              <li key={b}><a href={url(b)} target="_blank" rel="noreferrer">{b}</a></li>
            ))}
            {berkas.some((b) => b.startsWith("kerja/")) && (
              <li>
                <details>
                  <summary>Hasil kerja tiap agen ({berkas.filter((b) => b.startsWith("kerja/")).length} berkas)</summary>
                  <ul>
                    {berkas.filter((b) => b.startsWith("kerja/")).map((b) => (
                      <li key={b}><a href={url(b)} target="_blank" rel="noreferrer">{b.replace("kerja/", "")}</a></li>
                    ))}
                  </ul>
                </details>
              </li>
            )}
          </ul>
        </section>

        {s.status !== "PENDING" && (
          <section className="bagian">
            <h2>Keputusan</h2>
            <p>{s.status === "DICAIRKAN" ? "Disetujui dan dicairkan" : "Ditolak"} oleh {s.diputuskan_oleh}{s.alasan ? ` — “${s.alasan}”` : ""}.</p>
          </section>
        )}

        <footer className="sidik">
          Sidik versi <code>{s.manifest_hash.slice(0, 16)}</code> dihitung backend atas {berkas.length} berkas saat diajukan.
          Bila agen mengubah satu berkas pun setelah ini, pencairan otomatis ditolak.
        </footer>
      </article>

      {(bisaPutuskan || galat) && (
        <div className="keputusan">
          <div className="keputusan-isi">
            {galat && <p className="galat" role="alert">{galat}</p>}
            {bisaPutuskan && mode === "lihat" && (
              <>
                {tinggi && (
                  <label className="cek-risiko">
                    <input type="checkbox" checked={cek} onChange={(e) => setCek(e.target.checked)} />
                    <span><strong>Risiko tinggi:</strong> {s.alasan_risiko.join("; ")}. Saya sudah memeriksa temuan dan berkasnya.</span>
                  </label>
                )}
                <div className="keputusan-tombol">
                  <button type="button" className="tombol" onClick={() => { setMode("tolak"); setGalat(""); }} disabled={proses}>Tolak</button>
                  <button type="button" className="tombol-utama" onClick={() => putuskan("setujui")} disabled={proses || (tinggi && !cek)}>
                    {proses ? "Mencairkan…" : "Setujui & cairkan"}
                  </button>
                </div>
              </>
            )}
            {bisaPutuskan && mode === "tolak" && (
              <>
                <label className="label" htmlFor="alasan">Alasan penolakan (dibaca tim agen untuk perbaikan)</label>
                <textarea id="alasan" value={alasan} onChange={(e) => setAlasan(e.target.value)} placeholder="Mis. boarding pass atas nama orang lain, minta bukti pengganti" autoFocus />
                <div className="keputusan-tombol">
                  <button type="button" className="tombol" onClick={() => { setMode("lihat"); setGalat(""); }} disabled={proses}>Kembali</button>
                  <button type="button" className="tombol-bahaya" onClick={() => putuskan("tolak")} disabled={proses}>Tolak SPJ</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <LembarSPJ />
    </Shell>
  );
}
