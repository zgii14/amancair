"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import LangkahStatus from "@/components/LangkahStatus";
import PapanAgen from "@/components/PapanAgen";
import Shell, { useSesi } from "@/components/Shell";
import { agenAktif, api, ApiError, type KasusDetail, type Progres } from "@/lib/api";
import { tanggal } from "@/lib/format";
import { rupiah } from "@/lib/rupiah";

const NAMA_AGEN: Record<string, string> = {
  koordinator: "Koordinator",
  "pembaca-tiket": "Pembaca Tiket",
  "pembaca-hotel": "Pembaca Hotel",
  "pembaca-struk": "Pembaca Struk",
  "verifikator-sbm": "Verifikator SBM",
  auditor: "Auditor",
  "penyusun-spj": "Penyusun SPJ",
  jembatan: "Jembatan",
  pipeline_skrip: "Pipeline skrip",
};

function jam(iso: string) {
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" })
    .format(new Date(iso));
}

function ProsesKasus() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSesi();
  const [k, setK] = useState<KasusDetail | null>(null);
  const [progres, setProgres] = useState<Progres[]>([]);
  const [tidakAda, setTidakAda] = useState(false);
  const [putar, setPutar] = useState<number | null>(null);
  const terakhir = useRef(0);

  useEffect(() => {
    let hidup = true;
    const muat = async () => {
      try {
        const d = await api<KasusDetail>(`/kasus/${id}?setelah=${terakhir.current}`);
        if (!hidup) return;
        setK(d);
        if (d.progres.length) {
          terakhir.current = Math.max(...d.progres.map((p) => p.id));
          setProgres((lama) => [...lama, ...d.progres].sort((a, b) => a.waktu.localeCompare(b.waktu) || a.id - b.id));
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) setTidakAda(true);
      }
    };
    muat();
    const t = setInterval(muat, 2000);
    return () => {
      hidup = false;
      clearInterval(t);
    };
  }, [id]);

  // Putar ulang: menampilkan kejadian asli satu per satu, dipercepat. Urutan dan isinya tidak diubah.
  useEffect(() => {
    if (putar === null) return;
    if (putar >= progres.length) {
      const t = setTimeout(() => setPutar(null), 1500);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setPutar(putar + 1), 700);
    return () => clearTimeout(t);
  }, [putar, progres.length]);

  if (tidakAda) {
    return (
      <div className="kosong" style={{ marginTop: 24 }}>
        <h2>Pengajuan tidak ditemukan</h2>
        <p><Link href={me.jabatan === "Staf" ? "/pengajuan" : "/proses"}>Kembali ke daftar</Link></p>
      </div>
    );
  }
  if (!k) return <p className="info" role="status" style={{ marginTop: 24 }}>Memuat…</p>;

  const tampil = putar === null ? progres : progres.slice(0, putar);
  const statusTampil = putar === null ? k.status : putar < progres.length ? "DIPERIKSA_AGEN" : k.status;
  const pakaiSkrip = progres.some((p) => p.agen === "pipeline_skrip");
  const aktif = agenAktif(k);
  const live = aktif && putar === null;
  const terhenti = k.status === "DIPERIKSA_AGEN" && !aktif && putar === null;

  return (
    <>
      <p className="remah"><Link href={me.jabatan === "Staf" ? "/pengajuan" : "/proses"}>← Kembali</Link></p>
      <h1 className="judul-halaman">
        {k.nomor_spj}
        {live && <span className="lencana-live" role="status"><i aria-hidden="true" /> Sedang berjalan</span>}
        {putar !== null && <span className="lencana-live putar" role="status">Putar ulang</span>}
      </h1>
      <p className="sub-halaman">
        {k.nama_pegawai ?? "Kasus uji proyek WorkBuddy"}{k.tujuan ? ` · ${k.tujuan}` : ""}
        {k.tanggal_berangkat && k.tanggal_kembali ? ` · ${tanggal(k.tanggal_berangkat)} s.d. ${tanggal(k.tanggal_kembali)}` : ""}
      </p>

      <LangkahStatus status={statusTampil} />

      {k.spj && (
        <div className="ringkas-spj">
          <span>Diajukan {rupiah(k.spj.total_diajukan)} · akan dibayar <strong>{rupiah(k.spj.total_dibayar)}</strong></span>
          <span>{k.spj.jumlah_temuan} temuan{k.spj.risiko === "tinggi" ? " · risiko tinggi" : ""}</span>
          {k.spj.alasan && <span className="galat">Alasan ditolak: {k.spj.alasan}</span>}
          {me.boleh_menyetujui && <Link href={`/spj/${k.spj.nomor}`}>Buka lembar SPJ →</Link>}
        </div>
      )}

      {terhenti && k.aktivitas_terakhir && (
        <p className="info" style={{ marginTop: 12 }}>
          Tidak ada aktivitas tim agen sejak {jam(k.aktivitas_terakhir)}. SPJ belum diajukan ke bendahara.
        </p>
      )}

      {pakaiSkrip && (
        <p className="peringatan-kecil">
          Sebagian kasus ini diproses pipeline skrip, bukan tim agen terpisah. Ditampilkan apa adanya.
        </p>
      )}

      <div className="proses-kisi">
        <section aria-labelledby="judul-tim">
          <div className="judul-baris">
            <h2 id="judul-tim" className="subjudul">Tahapan pemeriksaan</h2>
            {progres.length > 0 && !live && (
              <button type="button" className="tombol kecil" onClick={() => setPutar(0)} disabled={putar !== null}>
                Putar ulang
              </button>
            )}
          </div>
          <PapanAgen progres={tampil} status={statusTampil} aktif={putar !== null || aktif} />
        </section>

        <section aria-labelledby="judul-jejak">
          <h2 id="judul-jejak" className="subjudul">Jejak aktivitas</h2>
          {tampil.length === 0 ? (
            <div className="kosong">
              <p>Belum ada aktivitas. Halaman ini diperbarui otomatis setiap 2 detik.</p>
            </div>
          ) : (
            <ol className="jejak" aria-live="polite">
              {[...tampil].reverse().map((p) => (
                <li key={p.id} className="jejak-baris">
                  <span className="jejak-waktu">{jam(p.waktu)}</span>
                  <span className="jejak-agen">{NAMA_AGEN[p.agen] ?? p.agen} · {p.aksi.replaceAll("_", " ")}</span>
                  {p.pesan && <span className="jejak-pesan">{p.pesan}</span>}
                </li>
              ))}
            </ol>
          )}
          <p className="info catatan-sumber">
            &ldquo;Selesai&rdquo; diambil dari waktu tulis berkas hasil tiap agen dan log audit tim di WorkBuddy.
            &ldquo;Sedang bekerja&rdquo; disimpulkan dari urutan tim: agen yang syaratnya sudah selesai tetapi berkasnya belum ada.
          </p>
        </section>
      </div>

      {k.berkas.length > 0 && (
        <>
          <h2 className="subjudul">Bukti yang diunggah</h2>
          <ul className="daftar-berkas">
            {k.berkas.map((b) => (
              <li key={b}><a href={`/api/kasus/${k.id}/berkas/${encodeURIComponent(b)}`} target="_blank" rel="noreferrer">{b}</a></li>
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
      <ProsesKasus />
    </Shell>
  );
}
