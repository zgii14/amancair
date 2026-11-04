import type { Asal } from "@/lib/api";

const TEKS: Record<Asal, { label: string; arti: string }> = {
  pimpinan: { label: "Instruksi pimpinan", arti: "Diambil dari permintaan pimpinan sendiri." },
  direktori: { label: "Direktori", arti: "Dicocokkan dari direktori pegawai resmi." },
  surat: { label: "Dari isi surat", arti: "Hanya disebut di dalam dokumen, bukan diminta pimpinan. Periksa sebelum menyetujui." },
};

export default function AsalChip({ asal }: { asal: Asal }) {
  const t = TEKS[asal];
  return (
    <span className={`asal asal-${asal}`} title={t.arti}>
      {t.label}
      <span className="sr-only">: {t.arti}</span>
    </span>
  );
}
