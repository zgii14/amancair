"use client";

import Link from "next/link";
import { useState } from "react";
import Shell from "@/components/Shell";
import { ApiError, post, type Kasus } from "@/lib/api";

const BATAS = 5 * 1024 * 1024;
const TERIMA = ".txt,.pdf,.jpg,.jpeg,.png";

function bacaBase64(f: File): Promise<string> {
  return new Promise((ok, gagal) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",", 2)[1] ?? "");
    r.onerror = () => gagal(r.error);
    r.readAsDataURL(f);
  });
}

function FormPengajuan() {
  const [tujuan, setTujuan] = useState("");
  const [maksud, setMaksud] = useState("");
  const [berangkat, setBerangkat] = useState("");
  const [kembali, setKembali] = useState("");
  const [catatan, setCatatan] = useState("");
  const [berkas, setBerkas] = useState<File[]>([]);
  const [galat, setGalat] = useState("");
  const [proses, setProses] = useState(false);
  const [hasil, setHasil] = useState<Kasus | null>(null);

  function tambah(files: FileList | null) {
    if (!files) return;
    const baru = [...berkas];
    for (const f of Array.from(files)) {
      if (f.size > BATAS) {
        setGalat(`${f.name} lebih dari 5 MB.`);
        continue;
      }
      if (!baru.some((b) => b.name === f.name)) baru.push(f);
    }
    setBerkas(baru);
  }

  async function kirim(e: React.FormEvent) {
    e.preventDefault();
    if (!tujuan.trim() || maksud.trim().length < 5 || !berangkat || !kembali) {
      setGalat("Lengkapi tujuan, maksud perjalanan, dan tanggal.");
      return;
    }
    if (berkas.length === 0) {
      setGalat("Unggah minimal satu bukti.");
      return;
    }
    setProses(true);
    setGalat("");
    try {
      const isi = await Promise.all(berkas.map(async (f) => ({ nama: f.name, isi_base64: await bacaBase64(f) })));
      setHasil(await post<Kasus>("/kasus", {
        tujuan: tujuan.trim(), maksud: maksud.trim(), tanggal_berangkat: berangkat, tanggal_kembali: kembali,
        catatan: catatan.trim(), berkas: isi,
      }));
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal mengirim. Coba lagi.");
    } finally {
      setProses(false);
    }
  }

  if (hasil) {
    return (
      <div className="kosong" style={{ marginTop: 24 }}>
        <h2>Pengajuan {hasil.nomor_spj} diterima</h2>
        <p>Bukti Anda akan diperiksa otomatis. Anda bisa memantau prosesnya dari halaman SPJ saya.</p>
        <p style={{ marginTop: 12 }}>
          <Link className="tombol tombol-utama" href={`/proses/${hasil.id}`}>Lihat proses</Link>
        </p>
      </div>
    );
  }

  return (
    <form className="form-pengajuan" onSubmit={kirim} noValidate>
      <h1 className="judul-halaman">Ajukan SPJ perjalanan dinas</h1>
      <p className="sub-halaman">Unggah bukti apa adanya. Sistem yang membaca, menghitung, dan mencocokkan dengan aturan.</p>
      <label>
        Kota tujuan
        <input value={tujuan} onChange={(e) => setTujuan(e.target.value)} placeholder="Makassar" />
      </label>
      <label>
        Maksud perjalanan
        <input value={maksud} onChange={(e) => setMaksud(e.target.value)} placeholder="Bimbingan teknis keamanan siber" />
      </label>
      <div className="dua-kolom">
        <label>
          Tanggal berangkat
          <input type="date" value={berangkat} onChange={(e) => setBerangkat(e.target.value)} />
        </label>
        <label>
          Tanggal kembali
          <input type="date" value={kembali} onChange={(e) => setKembali(e.target.value)} />
        </label>
      </div>
      <label>
        Catatan untuk pemeriksa (opsional)
        <textarea rows={3} value={catatan} onChange={(e) => setCatatan(e.target.value)} />
      </label>
      <label className="unggah">
        <span>Bukti: tiket, boarding pass, invoice hotel, struk (.txt, .pdf, .jpg, .png, maks. 5 MB)</span>
        <input type="file" multiple accept={TERIMA} onChange={(e) => { tambah(e.target.files); e.target.value = ""; }} />
      </label>
      {berkas.length > 0 && (
        <ul className="daftar-berkas">
          {berkas.map((f) => (
            <li key={f.name}>
              {f.name} <span className="info">({Math.ceil(f.size / 1024)} KB)</span>
              <button type="button" className="tombol-teks" onClick={() => setBerkas(berkas.filter((b) => b !== f))}>Hapus</button>
            </li>
          ))}
        </ul>
      )}
      {galat && <p className="galat" role="alert">{galat}</p>}
      <button className="tombol tombol-utama" type="submit" disabled={proses}>{proses ? "Mengirim…" : "Kirim pengajuan"}</button>
    </form>
  );
}

export default function Page() {
  return (
    <Shell>
      <FormPengajuan />
    </Shell>
  );
}
