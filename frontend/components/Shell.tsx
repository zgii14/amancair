"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, post, type Kontak, type Me, type ProfilOrg, type Rencana } from "@/lib/api";

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

const NAV = [
  { href: "/", label: "Antrean" },
  { href: "/riwayat", label: "Riwayat" },
  { href: "/audit", label: "Jejak audit" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [profil, setProfil] = useState<ProfilOrg | null>(null);
  const [menunggu, setMenunggu] = useState<number | null>(null);

  const segarkanHitung = useCallback(() => {
    api<Rencana[]>("/rencana?status=PENDING").then((r) => setMenunggu(r.length)).catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([api<Me>("/me"), api<ProfilOrg>("/profil")]).then(([m, p]) => {
      setMe(m);
      setProfil(p);
    }).catch(() => {});
    segarkanHitung();
  }, [segarkanHitung]);

  async function keluar() {
    await post("/logout").catch(() => {});
    window.location.href = "/login";
  }

  if (!me || !profil) {
    return <p className="wadah info" style={{ paddingTop: 24 }} role="status">Memuat meja…</p>;
  }

  const kontak = (id: string) => profil.kontak.find((k) => k.id === id);
  const aktif = (href: string) => (href === "/" ? pathname === "/" || pathname.startsWith("/rencana") : pathname.startsWith(href));

  return (
    <SesiContext.Provider value={{ me, profil, kontak, segarkanHitung }}>
      <header className="kepala">
        <div className="kepala-isi">
          <div className="kepala-baris">
            <div className="merek">
              Meja Pimpinan
              <small>{profil.nama_org}</small>
            </div>
            <div className="siapa">
              <strong>{me.nama}</strong> · {me.jabatan}
              <button type="button" className="tombol-keluar" onClick={keluar}>Keluar</button>
            </div>
          </div>
          <nav className="nav" aria-label="Navigasi utama">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} aria-current={aktif(n.href) ? "page" : undefined}>
                {n.label}
                {n.href === "/" && menunggu ? (
                  <span className="hitung" aria-label={`${menunggu} menunggu keputusan`}>{menunggu}</span>
                ) : null}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="wadah">{children}</main>
    </SesiContext.Provider>
  );
}
