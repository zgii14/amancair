"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, post, type Kontak, type Me, type ProfilOrg } from "@/lib/api";

type Sesi = {
  me: Me;
  profil: ProfilOrg;
  kontak: (id: string) => Kontak | undefined;
  segarkanHitung: () => void;
};

const SesiContext = createContext<Sesi | null>(null);

export function useSesi(): Sesi {
  const s = useContext(SesiContext);
  if (!s) throw new Error("useSesi harus di dalam <Shell>");
  return s;
}

type Ikon = "beranda" | "masuk" | "proses" | "audit" | "riwayat" | "daftar" | "tambah";

// Ikon garis sederhana 20px, mengikuti warna teks.
const PATH: Record<Ikon, string> = {
  beranda: "M3 10.5 10 4l7 6.5M5 9v7h4v-4h2v4h4V9",
  masuk: "M3 11h4l1.5 2h3L13 11h4M3 11l2-6h10l2 6v5H3z",
  proses: "M4 5h12M4 10h12M4 15h7M14.5 13.5l1.5 1.5 3-3",
  audit: "M10 3 4 5.5v4.5c0 3.5 2.6 6.2 6 7 3.4-.8 6-3.5 6-7V5.5zM7.5 10l2 2 3.5-3.5",
  riwayat: "M10 5v5l3 2M3.5 10a6.5 6.5 0 1 0 2-4.7M3 3.5V7h3.5",
  daftar: "M6 3h6l4 4v10H6zM12 3v4h4M8.5 11h5M8.5 14h5",
  tambah: "M10 4v12M4 10h12",
};

function Simbol({ nama }: { nama: Ikon }) {
  return (
    <svg className="ikon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <path d={PATH[nama]} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type Menu = { href: string; label: string; ikon: Ikon; hitung?: boolean };

const NAV_DISPOSISI: Menu[] = [
  { href: "/", label: "Antrean", ikon: "masuk", hitung: true },
  { href: "/riwayat", label: "Riwayat", ikon: "riwayat" },
  { href: "/audit", label: "Jejak audit", ikon: "audit" },
];
const NAV_SPJ: Menu[] = [
  { href: "/beranda", label: "Beranda", ikon: "beranda" },
  { href: "/spj", label: "SPJ menunggu", ikon: "masuk", hitung: true },
  { href: "/proses", label: "Proses pemeriksaan", ikon: "proses" },
  { href: "/audit", label: "Jejak audit", ikon: "audit" },
];
const NAV_PEGAWAI: Menu[] = [
  { href: "/pengajuan", label: "SPJ saya", ikon: "daftar" },
  { href: "/pengajuan/baru", label: "Ajukan SPJ", ikon: "tambah" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [profil, setProfil] = useState<ProfilOrg | null>(null);
  const [menunggu, setMenunggu] = useState<number | null>(null);
  const [buka, setBuka] = useState(false);

  const segarkanHitung = useCallback(() => {
    api<Me>("/me")
      .then((m) => {
        if (m.profil === "diskominfo" && m.jabatan === "Staf") return [];
        return api<unknown[]>(m.profil === "diskominfo" ? "/spj?status=PENDING" : "/rencana?status=PENDING");
      })
      .then((r) => setMenunggu(r.length))
      .catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([api<Me>("/me"), api<ProfilOrg>("/profil")]).then(([m, p]) => {
      setMe(m);
      setProfil(p);
    }).catch(() => {});
    segarkanHitung();
  }, [segarkanHitung]);

  useEffect(() => setBuka(false), [pathname]);
  useEffect(() => {
    if (!buka) return;
    const tutup = (e: KeyboardEvent) => e.key === "Escape" && setBuka(false);
    window.addEventListener("keydown", tutup);
    return () => window.removeEventListener("keydown", tutup);
  }, [buka]);

  async function keluar() {
    await post("/logout").catch(() => {});
    window.location.href = "/login";
  }

  if (!me || !profil) {
    return <p className="info" style={{ padding: 24 }} role="status">Memuat…</p>;
  }

  const kontak = (id: string) => profil.kontak.find((k) => k.id === id);
  const NAV = me.profil !== "diskominfo" ? NAV_DISPOSISI : me.jabatan === "Staf" ? NAV_PEGAWAI : NAV_SPJ;
  const aktif = (href: string) => {
    if (href === "/") return pathname === "/" || pathname.startsWith("/rencana");
    // "/pengajuan" jangan ikut menyala saat di "/pengajuan/baru"
    if (NAV.some((n) => n.href !== href && n.href.startsWith(href) && pathname.startsWith(n.href))) return false;
    if (href === "/proses") return pathname.startsWith("/proses");
    return pathname.startsWith(href);
  };
  const inisial = me.nama.split(" ").map((k) => k[0]).slice(0, 2).join("");

  return (
    <SesiContext.Provider value={{ me, profil, kontak, segarkanHitung }}>
      <div className="aplikasi" data-menu={buka ? "buka" : "tutup"}>
        <header className="bilah-atas">
          <button type="button" className="tombol-menu" aria-expanded={buka} aria-controls="menu-samping"
            onClick={() => setBuka(!buka)}>
            <span aria-hidden="true">☰</span> Menu
          </button>
          <span className="bilah-judul">Meja Pimpinan</span>
        </header>

        {buka && <button type="button" className="tirai" aria-label="Tutup menu" onClick={() => setBuka(false)} />}

        <aside className="samping" id="menu-samping">
          <div className="merek">
            <span className="merek-nama">Meja Pimpinan</span>
            <span className="merek-org">{profil.nama_org}</span>
          </div>
          <nav className="menu" aria-label="Menu utama">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} aria-current={aktif(n.href) ? "page" : undefined}>
                <Simbol nama={n.ikon} />
                <span className="menu-label">{n.label}</span>
                {n.hitung && menunggu ? (
                  <span className="hitung" aria-label={`${menunggu} menunggu keputusan`}>{menunggu}</span>
                ) : null}
              </Link>
            ))}
          </nav>
          <div className="pengguna">
            <span className="avatar" aria-hidden="true">{inisial}</span>
            <span className="pengguna-isi">
              <strong>{me.nama}</strong>
              <span>{me.jabatan}</span>
            </span>
            <button type="button" className="tombol-keluar" onClick={keluar}>Keluar</button>
          </div>
        </aside>

        <main className="isi">
          <div className="wadah">{children}</div>
        </main>
      </div>
    </SesiContext.Provider>
  );
}
