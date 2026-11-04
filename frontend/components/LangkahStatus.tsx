import type { StatusKasus } from "@/lib/api";

const LANGKAH: { id: StatusKasus; label: string }[] = [
  { id: "DITERIMA", label: "Diterima" },
  { id: "DIPERIKSA_AGEN", label: "Sedang diperiksa" },
  { id: "MENUNGGU_BENDAHARA", label: "Menunggu bendahara" },
  { id: "DICAIRKAN", label: "Dicairkan" },
];

export const LABEL_STATUS: Record<StatusKasus, string> = {
  DITERIMA: "Diterima",
  DIPERIKSA_AGEN: "Sedang diperiksa",
  MENUNGGU_BENDAHARA: "Menunggu bendahara",
  DICAIRKAN: "Dicairkan",
  DITOLAK: "Ditolak",
};

export default function LangkahStatus({ status }: { status: StatusKasus }) {
  const ditolak = status === "DITOLAK";
  const posisi = ditolak ? 3 : LANGKAH.findIndex((l) => l.id === status);
  return (
    <ol className="langkah" aria-label={`Status: ${LABEL_STATUS[status]}`}>
      {LANGKAH.map((l, i) => {
        const terakhir = i === LANGKAH.length - 1;
        const label = terakhir && ditolak ? "Ditolak" : l.label;
        const keadaan = i < posisi ? "lewat" : i === posisi ? (ditolak ? "tolak" : terakhir ? "lewat" : "kini") : "nanti";
        return (
          <li key={l.id} data-keadaan={keadaan} aria-current={i === posisi ? "step" : undefined}>
            <span className="titik" aria-hidden="true" />
            {label}
          </li>
        );
      })}
    </ol>
  );
}
