"use client";

import { useState } from "react";
import { post } from "@/lib/api";

const AKUN: Record<string, { label: string; contoh: string }> = {
  diskominfo: { label: "Diskominfo Kab. Sejahtera (SPJ)", contoh: "sri" },
  perusahaan: { label: "PT Nusantara Logistik", contoh: "rina" },
  kecamatan: { label: "Kecamatan Sukamaju", contoh: "camat_andi" },
};

// Akun dummy untuk demo; semua memakai kata sandi demo yang sama.
const AKUN_DEMO = [
  { id: "sri", label: "Sri Wahyuni", peran: "Bendahara" },
  { id: "budi_santoso", label: "Budi Santoso", peran: "Pegawai" },
  { id: "lestari", label: "Lestari Dewi", peran: "Pegawai" },
  { id: "ahmad", label: "Ahmad Fauzi", peran: "Kepala Dinas" },
];

export default function LoginPage() {
  const [profil, setProfil] = useState("diskominfo");
  const [username, setUsername] = useState("sri");
  const [password, setPassword] = useState("");
  const [galat, setGalat] = useState("");
  const [proses, setProses] = useState(false);

  async function masuk(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setGalat("Isi ID pegawai dan kata sandi.");
      return;
    }
    setProses(true);
    setGalat("");
    try {
      const me = await post<{ jabatan: string }>("/login", { profil, username: username.trim(), password });
      window.location.href = profil !== "diskominfo" ? "/" : me.jabatan === "Staf" ? "/pengajuan" : "/beranda";
    } catch {
      setGalat("ID pegawai atau kata sandi salah.");
      setProses(false);
    }
  }

  return (
    <main className="masuk">
      <form onSubmit={masuk} noValidate>
        <div>
          <h1>Meja Pimpinan</h1>
          <p className="info">{profil === "diskominfo" ? "Pegawai mengajukan SPJ, sistem memeriksa, bendahara memutuskan." : "Tinjau rencana yang disiapkan agent, lalu putuskan."}</p>
        </div>
        <label>
          Organisasi
          <select
            value={profil}
            onChange={(e) => {
              setProfil(e.target.value);
              setUsername(AKUN[e.target.value].contoh);
            }}
          >
            {Object.entries(AKUN).map(([id, a]) => (
              <option key={id} value={id}>{a.label}</option>
            ))}
          </select>
        </label>
        {profil === "diskominfo" && (
          <fieldset className="akun-demo">
            <legend>Akun demo</legend>
            {AKUN_DEMO.map((a) => (
              <button key={a.id} type="button" aria-pressed={username === a.id} onClick={() => setUsername(a.id)}>
                <strong>{a.label}</strong>
                <span>{a.peran}</span>
              </button>
            ))}
          </fieldset>
        )}
        <label>
          ID pegawai
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Kata sandi
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        {galat && <p className="galat" role="alert">{galat}</p>}
        <button className="tombol-utama" type="submit" disabled={proses}>{proses ? "Memeriksa…" : "Masuk"}</button>
      </form>
    </main>
  );
}
