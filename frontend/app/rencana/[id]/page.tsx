"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import AsalChip from "@/components/AsalChip";
import Shell, { useSesi } from "@/components/Shell";
import { api, ApiError, post, type Aksi, type Nilai, type Rencana } from "@/lib/api";
import { JENIS_AKSI, SIFAT, tanggal, waktuLokal, waktuRapat } from "@/lib/format";

const CAP: Record<string, { teks: string; warna?: string; kecil: string }> = {
  DISETUJUI: { teks: "Disetujui", kecil: "menunggu jeda kirim" },
  DIEKSEKUSI: { teks: "Terkirim", kecil: "sudah dieksekusi" },
  DITOLAK: { teks: "Ditolak", warna: "merah", kecil: "tidak dikirim" },
  DIBATALKAN: { teks: "Dibatalkan", warna: "abu", kecil: "pengiriman ditarik" },
};

function Penerima({ p }: { p: Nilai }) {
  const { kontak } = useSesi();
  const k = kontak(p.nilai);
  return (
    <li>
      <span className="nama">{k ? k.nama : p.nilai}</span>
      <AsalChip asal={p.asal} />
      <span className="detail">
        {k ? `${k.jabatan} · ${k.email} · ${k.zona}` : "Di luar direktori pegawai"}
      </span>
    </li>
  );
}

function KotakAksi({ a, i, total }: { a: Aksi; i: number; total: number }) {
  const { profil } = useSesi();
  return (
    <section className="aksi" aria-labelledby={`aksi-${i}`}>
      <div className="aksi-kepala">
        <h2 id={`aksi-${i}`}>{JENIS_AKSI[a.jenis]}</h2>
        <span>Aksi {i + 1} dari {total}</span>
      </div>
      <div className="baris">
        <span className="label">{a.jenis === "disposisi" ? "Diteruskan kepada" : "Kepada"}</span>
        <ul className="penerima">
          {a.penerima.map((p) => <Penerima key={p.nilai} p={p} />)}
        </ul>
      </div>
      {a.waktu_mulai && (
        <div className="baris">
          <span className="label">Waktu</span>
          <div>
            <strong>{waktuRapat(a.waktu_mulai.nilai)}</strong> · {a.durasi_menit} menit{" "}
            <AsalChip asal={a.waktu_mulai.asal} />
          </div>
        </div>
      )}
      <div className="baris">
        <span className="label">Perihal</span>
        <strong>{a.judul}</strong>
      </div>
      <div className="baris">
        <span className="label">Isi</span>
        <div>
          <div className="isi-surat">{a.isi.nilai}</div>
          <div style={{ marginTop: 6 }}><AsalChip asal={a.isi.asal} /></div>
        </div>
      </div>
      {a.jenis === "disposisi" && (
        <div className="baris">
          <span className="label">Instruksi</span>
          <ul className="instruksi" aria-label="Instruksi disposisi baku">
            {profil.instruksi_disposisi.map((ins) => {
              const dipilih = ins.toLowerCase() === a.instruksi?.toLowerCase();
              return (
                <li key={ins} data-dipilih={dipilih ? "ya" : "tidak"}>
                  {ins}
                  {dipilih && <span className="sr-only"> (dipilih)</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {a.tenggat && (
        <div className="baris">
          <span className="label">Tenggat</span>
          <strong>{tanggal(a.tenggat)}</strong>
        </div>
      )}
    </section>
  );
}

function Lembar() {
  const { id } = useParams<{ id: string }>();
  const { me, profil, kontak, segarkanHitung } = useSesi();
  const [r, setR] = useState<Rencana | null>(null);
  const [tidakAda, setTidakAda] = useState(false);
  const [mode, setMode] = useState<"lihat" | "tolak">("lihat");
  const [alasan, setAlasan] = useState("");
  const [cekRisiko, setCekRisiko] = useState(false);
  const [galat, setGalat] = useState("");
  const [proses, setProses] = useState(false);
  const [undoSampai, setUndoSampai] = useState<number | null>(null);
  const [sekarang, setSekarang] = useState(() => Date.now());
  const [capBaru, setCapBaru] = useState(false);

  const muat = useCallback(async () => {
    try {
      setR(await api<Rencana>(`/rencana/${id}`));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setTidakAda(true);
    }
  }, [id]);

  useEffect(() => {
    muat();
    const tersimpan = sessionStorage.getItem(`undo:${id}`);
    if (tersimpan) setUndoSampai(Number(tersimpan));
  }, [id, muat]);

  useEffect(() => {
    if (!undoSampai) return;
    const t = setInterval(() => setSekarang(Date.now()), 1000);
    return () => clearInterval(t);
  }, [undoSampai]);

  const sisaDetik = undoSampai ? Math.max(0, Math.ceil((undoSampai - sekarang) / 1000)) : 0;

  useEffect(() => {
    if (r?.status !== "DISETUJUI" || sisaDetik > 0) return;
    const t = setInterval(muat, 2000);
    return () => clearInterval(t);
  }, [r?.status, sisaDetik, muat]);

  async function setujui() {
    setProses(true);
    setGalat("");
    try {
      const res = await post<{ bisa_undo_sampai: string }>(`/rencana/${id}/setujui`, { konfirmasi_risiko: cekRisiko });
      const batas = new Date(res.bisa_undo_sampai).getTime();
      sessionStorage.setItem(`undo:${id}`, String(batas));
      setUndoSampai(batas);
      setSekarang(Date.now());
      setCapBaru(true);
      await muat();
      segarkanHitung();
    } catch (e) {
      setGalat(e instanceof ApiError ? e.message : "Gagal menyetujui. Coba lagi.");
    } finally {
      setProses(false);
    }
  }

  async function tolak() {
    if (!alasan.trim()) {
      setGalat("Tulis alasan agar agent bisa menyusun ulang rencananya.");
      return;
    }
    setProses(true);
    setGalat("");
    try {
      await post(`/rencana/${id}/tolak`, { alasan: alasan.trim() });
      setCapBaru(true);
      setMode("lihat");
      await muat();
      segarkanHitung();
    } catch (e) {
      setGalat(e instanceof ApiError ? e.message : "Gagal menolak. Coba lagi.");
    } finally {
      setProses(false);
    }
  }

  async function batalkan() {
    setProses(true);
    setGalat("");
    try {
      await post(`/rencana/${id}/undo`);
      sessionStorage.removeItem(`undo:${id}`);
      setUndoSampai(null);
      setCapBaru(true);
      await muat();
    } catch (e) {
      setGalat(e instanceof ApiError ? e.message : "Gagal membatalkan.");
    } finally {
      setProses(false);
    }
  }

  if (tidakAda) {
    return (
      <div className="kosong" style={{ marginTop: 24 }}>
        <h2>Rencana tidak ditemukan</h2>
        <p><Link href="/">Kembali ke antrean</Link></p>
      </div>
    );
  }
  if (!r) return <p className="info" role="status" style={{ marginTop: 24 }}>Memuat lembar disposisi…</p>;

  const pengaju = kontak(r.pengaju);
  const cap = CAP[r.status];
  const tinggi = r.risiko === "tinggi";
  const bisaPutuskan = r.status === "PENDING" && me.boleh_menyetujui;
  const masihBisaUndo = r.status === "DISETUJUI" && sisaDetik > 0;

  return (
    <>
      <p style={{ marginTop: 16 }}><Link href="/">← Antrean</Link></p>
      <article className="lembar" aria-labelledby="perihal">
        {cap && (
          <div className="cap" data-warna={cap.warna} data-baru={capBaru ? "ya" : "tidak"} aria-hidden="true">
            {cap.teks}
            <small>{cap.kecil}</small>
          </div>
        )}
        <header className="kop">
          <div className="kop-label">Lembar disposisi · {profil.nama_org}</div>
          <h1 id="perihal">{r.surat.perihal ?? r.surat.ringkasan}</h1>
          {cap && <p className="sr-only">Status: {cap.teks}</p>}
        </header>
        <dl className="kisi">
          <div className="kotak"><dt>Dari</dt><dd>{r.surat.pengirim ?? "Tidak disebut"}</dd></div>
          <div className="kotak"><dt>Sifat</dt><dd>{SIFAT[r.surat.sifat]}</dd></div>
          <div className="kotak"><dt>Diajukan</dt><dd>{waktuLokal(r.dibuat)}</dd></div>
          <div className="kotak"><dt>Atas permintaan</dt><dd>{pengaju ? `${pengaju.nama}` : r.pengaju}</dd></div>
        </dl>

        {r.peringatan.length > 0 && (
          <section className="peringatan" role="alert" aria-label="Peringatan">
            <h2>Periksa sebelum menyetujui</h2>
            <ul>{r.peringatan.map((p) => <li key={p}>{p}</li>)}</ul>
          </section>
        )}

        <section className="bagian" aria-labelledby="isi-surat">
          <h2 id="isi-surat">Ringkasan surat</h2>
          <p>{r.surat.ringkasan}</p>
          {r.surat.kutipan_sumber.length > 0 && (
            <>
              <div className="label" style={{ marginTop: 12 }}>Bagian surat yang dirujuk</div>
              <ul className="kutipan">{r.surat.kutipan_sumber.map((k) => <li key={k}>“{k}”</li>)}</ul>
            </>
          )}
          <details className="asli">
            <summary>Lihat teks asli</summary>
            <pre>{r.surat.input_asli}</pre>
          </details>
        </section>

        {r.aksi.map((a, i) => <KotakAksi key={i} a={a} i={i} total={r.aksi.length} />)}

        {r.catatan_checker.length > 0 && (
          <section className="bagian" aria-labelledby="checker">
            <h2 id="checker">Catatan agent pemeriksa</h2>
            <ul style={{ margin: 0, paddingLeft: 18 }}>{r.catatan_checker.map((c) => <li key={c}>{c}</li>)}</ul>
          </section>
        )}

        <footer className="sidik">
          Sidik rencana <code>{r.hash.slice(0, 12)}</code>. Persetujuan terikat ke sidik ini; jika ada yang berubah, rencana perlu disetujui ulang.
        </footer>
      </article>

      {(bisaPutuskan || masihBisaUndo || galat) && (
        <div className="keputusan">
          <div className="keputusan-isi">
            {galat && <p className="galat" role="alert">{galat}</p>}

            {masihBisaUndo && (
              <>
                <div className="hitung-mundur" aria-live="polite">
                  <span>Dikirim dalam <strong>{sisaDetik}</strong> detik</span>
                  <button type="button" className="tombol-bahaya" onClick={batalkan} disabled={proses}>Batalkan pengiriman</button>
                </div>
                <div className="batang" aria-hidden="true"><span style={{ width: `${(sisaDetik / 60) * 100}%` }} /></div>
              </>
            )}

            {bisaPutuskan && mode === "lihat" && (
              <>
                {tinggi && (
                  <label className="cek-risiko">
                    <input type="checkbox" checked={cekRisiko} onChange={(e) => setCekRisiko(e.target.checked)} />
                    <span>
                      <strong>Risiko tinggi:</strong> {r.alasan_risiko.join("; ")}. Saya sudah memeriksa penerimanya.
                    </span>
                  </label>
                )}
                <div className="keputusan-tombol">
                  <button type="button" className="tombol" onClick={() => { setMode("tolak"); setGalat(""); }} disabled={proses}>Tolak</button>
                  <button type="button" className="tombol-utama" onClick={setujui} disabled={proses || (tinggi && !cekRisiko)}>
                    {proses ? "Menyetujui…" : "Setujui"}
                  </button>
                </div>
              </>
            )}

            {bisaPutuskan && mode === "tolak" && (
              <>
                <label className="label" htmlFor="alasan">Alasan penolakan (dibaca agent untuk menyusun ulang)</label>
                <textarea id="alasan" value={alasan} onChange={(e) => setAlasan(e.target.value)} placeholder="Mis. bukan Budi Santoso, tapi Budi Hartono" autoFocus />
                <div className="keputusan-tombol">
                  <button type="button" className="tombol" onClick={() => { setMode("lihat"); setGalat(""); }} disabled={proses}>Kembali</button>
                  <button type="button" className="tombol-bahaya" onClick={tolak} disabled={proses}>Tolak rencana</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {r.status === "PENDING" && !me.boleh_menyetujui && (
        <p className="info" style={{ marginTop: 12 }}>Anda dapat melihat rencana ini. Keputusan ada di tangan pimpinan yang berwenang.</p>
      )}
    </>
  );
}

export default function Page() {
  return (
    <Shell>
      <Lembar />
    </Shell>
  );
}
