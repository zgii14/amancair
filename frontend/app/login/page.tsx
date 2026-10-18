"use client";

import { useState } from "react";
import { post } from "@/lib/api";

const AKUN: Record<string, { label: string; contoh: string }> = {
  perusahaan: { label: "PT Nusantara Logistik", contoh: "rina" },
  kecamatan: { label: "Kecamatan Sukamaju", contoh: "camat_andi" },
};

export default function LoginPage() {
  const [profil, setProfil] = useState("perusahaan");
  const [username, setUsername] = useState("rina");
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
      await post("/login", { profil, username: username.trim(), password });
      window.location.href = "/";
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
          <p className="info">Tinjau rencana yang disiapkan agent, lalu putuskan.</p>
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
