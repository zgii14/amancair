import type { Metadata, Viewport } from "next";
import { Bitter, IBM_Plex_Mono, Public_Sans } from "next/font/google";
import "./globals.css";

const bitter = Bitter({ subsets: ["latin"], variable: "--font-judul", weight: ["500", "700", "800"] });
const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-isi" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-data", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Meja Pimpinan",
  description: "Tinjau dan putuskan rencana aksi yang disiapkan agent disposisi.",
};

export const viewport: Viewport = { themeColor: "#E6EBE3", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={`${bitter.variable} ${publicSans.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
