"use client";

import type { Progres, StatusKasus } from "@/lib/api";

type Keadaan = "menunggu" | "bekerja" | "selesai";

const AGEN: { id: string; nama: string; tugas: string }[] = [
  { id: "koordinator", nama: "Case Coordinator", tugas: "Membagi tugas dan menjaga urutan" },
  { id: "pembaca-tiket", nama: "Pembaca Tiket", tugas: "Tiket pesawat dan boarding pass" },
  { id: "pembaca-hotel", nama: "Pembaca Hotel", tugas: "Invoice dan malam menginap" },
  { id: "pembaca-struk", nama: "Pembaca Struk", tugas: "Taksi, makan, sidik struk" },
  { id: "verifikator-sbm", nama: "Verifikator SBM", tugas: "Cocokkan SPT, pagu, libur" },
  { id: "auditor", nama: "Auditor", tugas: "Periksa ulang, struk lintas SPJ" },
  { id: "penyusun-spj", nama: "Penyusun SPJ", tugas: "Rekap .xlsx, draf .docx" },
];

// Siapa harus selesai dulu sebelum agen ini bisa mulai (urutan di skill tim).
const SYARAT: Record<string, string[]> = {
  "pembaca-tiket": [],
  "pembaca-hotel": [],
  "pembaca-struk": [],
  "verifikator-sbm": ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"],
  auditor: ["verifikator-sbm"],
  "penyusun-spj": ["auditor"],
};

const LABEL: Record<Keadaan, string> = { menunggu: "Menunggu giliran", bekerja: "Sedang diproses", selesai: "Selesai" };

function jam(iso: string) {
  return new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso));
}

export function keadaanAgen(progres: Progres[], status: StatusKasus, aktif: boolean): Record<string, { keadaan: Keadaan; waktu?: string; pesan?: string }> {
  const berjalan = status === "DIPERIKSA_AGEN" && aktif;
  const selesaiAgen = (id: string) => progres.filter((p) => p.agen === id && p.aksi === "selesai").at(-1);
  const hasil: Record<string, { keadaan: Keadaan; waktu?: string; pesan?: string }> = {};
  for (const a of AGEN.slice(1)) {
    const s = selesaiAgen(a.id);
    const siap = SYARAT[a.id].every((x) => selesaiAgen(x));
    hasil[a.id] = s
      ? { keadaan: "selesai", waktu: s.waktu, pesan: s.pesan }
      : { keadaan: berjalan && siap ? "bekerja" : "menunggu" };
  }
  const semuaSelesai = AGEN.slice(1).every((a) => hasil[a.id].keadaan === "selesai");
  const terakhirKoor = progres.filter((p) => p.agen === "koordinator").at(-1);
  const lewat = status === "MENUNGGU_BENDAHARA" || status === "DICAIRKAN" || status === "DITOLAK";
  hasil.koordinator = semuaSelesai || lewat
    ? { keadaan: "selesai", waktu: terakhirKoor?.waktu, pesan: terakhirKoor?.pesan }
    : { keadaan: berjalan ? "bekerja" : "menunggu", pesan: terakhirKoor?.pesan };
  return hasil;
}

export default function PapanAgen({ progres, status, aktif }: { progres: Progres[]; status: StatusKasus; aktif: boolean }) {
  const k = keadaanAgen(progres, status, aktif);
  const kartu = (id: string, nomor: number) => {
    const a = AGEN.find((x) => x.id === id)!;
    const s = k[id];
    return (
      <li key={id} className="agen" data-keadaan={s.keadaan}>
        <div className="agen-ikon" aria-hidden="true">{s.keadaan === "selesai" ? "✓" : nomor}</div>
        <div className="agen-isi">
          <strong>{a.nama}</strong>
          <span className="agen-tugas">{a.tugas}</span>
          <span className="agen-status">
            {LABEL[s.keadaan]}
            {s.waktu && s.keadaan === "selesai" ? ` · ${jam(s.waktu)}` : ""}
          </span>
          {s.pesan && s.keadaan === "selesai" && <span className="agen-pesan">{s.pesan}</span>}
        </div>
      </li>
    );
  };
  const menungguBendahara = status === "MENUNGGU_BENDAHARA";
  const diputuskan = status === "DICAIRKAN" || status === "DITOLAK";

  return (
    <div className="papan">
      <ul className="papan-baris">{kartu("koordinator", 1)}</ul>
      <ul className="papan-baris tiga">
        {["pembaca-tiket", "pembaca-hotel", "pembaca-struk"].map((id) => kartu(id, 2))}
      </ul>
      <ul className="papan-baris">{kartu("verifikator-sbm", 3)}</ul>
      <ul className="papan-baris">{kartu("auditor", 4)}</ul>
      <ul className="papan-baris">{kartu("penyusun-spj", 5)}</ul>
      <ul className="papan-baris">
        <li className="agen manusia" data-keadaan={diputuskan ? "selesai" : menungguBendahara ? "giliran" : "menunggu"}>
          <div className="agen-ikon manusia-ikon" aria-hidden="true">{diputuskan ? "✓" : 6}</div>
          <div className="agen-isi">
            <strong>Bendahara Pengeluaran</strong>
            <span className="agen-tugas">Satu-satunya yang dapat menyetujui pencairan</span>
            <span className="agen-status">
              {diputuskan ? (status === "DICAIRKAN" ? "Sudah menyetujui" : "Menolak") : menungguBendahara ? "Menunggu keputusan" : "Belum giliran"}
            </span>
          </div>
        </li>
      </ul>
    </div>
  );
}
