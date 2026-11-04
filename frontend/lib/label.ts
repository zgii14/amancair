// Istilah untuk pengguna non-IT; sama dengan yang dipakai di dokumen draf SPJ.
export const TINGKAT: Record<string, string> = {
  KRITIS: "Sangat penting",
  TINGGI: "Penting",
  SEDANG: "Perlu dicek",
  RENDAH: "Informasi",
};

export const KELAS_TINGKAT: Record<string, string> = {
  KRITIS: "bahaya",
  TINGGI: "bahaya",
  SEDANG: "waspada",
  RENDAH: "",
};

export const HAL: Record<string, string> = {
  R01: "Di luar masa tugas",
  R02: "Nama pada bukti",
  R03: "Hotel melebihi batas biaya",
  R04: "Uang harian",
  R05: "Taksi melebihi batas biaya",
  R06: "Bukti ganda",
  R07: "Hari libur nasional",
  R08: "Nominal tidak terbaca",
  R09: "Tulisan perintah di dalam bukti",
  R10: "Perlu persetujuan khusus",
  R11: "Biaya makan",
  KELENGKAPAN: "Bukti belum lengkap",
  AUDITOR: "Catatan pemeriksa",
};

const BERKAS = /\b[\w-]+\.(?:txt|pdf|jpe?g|png)\b/gi;

/** Kalimat temuan dalam bahasa sehari-hari; nama berkas dipindah ke rujukan bukti. */
export function penjelasan(t: { aturan: string; deskripsi: string }): string {
  const d = t.deskripsi;
  const kutipan = d.match(/"([^"]+)"/)?.[1];
  const nilai = d.match(/Rp[\d.]+/)?.[0];
  if (t.aturan === "R09") {
    return `Di dalam bukti terdapat tulisan yang berisi perintah${kutipan ? `: “${kutipan}”` : ""}. Tulisan ini tidak diikuti dan tidak memengaruhi perhitungan.`;
  }
  if (t.aturan === "R11") return `Biaya makan${nilai ? ` ${nilai}` : ""} tidak dibayar karena sudah termasuk uang harian.`;
  if (t.aturan === "R06" && d.includes("sudah pernah diajukan")) {
    const nomor = d.match(/nomor ([^)]+)\)/)?.[1];
    const spj = d.match(/SPJ-\d{4}-\d{3}[a-z]?/)?.[0];
    return `Struk${nomor ? ` nomor ${nomor}` : ""} sudah pernah diajukan pada ${spj ?? "SPJ lain"}, sehingga tidak dapat dibayar lagi.`;
  }
  let s = d
    .replace(/\s*\((?:R\d{2}[^)]*|KELENGKAPAN)\)/g, "")
    .replace("Wajib konfirmasi tambahan bendahara:", "Perlu persetujuan khusus bendahara karena")
    .replace("ada item ditolak atau ditahan", "ada bagian yang ditolak atau ditahan")
    // Kata depan ikut dibuang bersama nama berkas: "di invoice_hotel.txt di luar" -> "di luar".
    .replace(/\s*\b(?:di|pada|dalam)\s+(?=[\w-]+\.(?:txt|pdf|jpe?g|png)\b)/gi, " ")
    .replace(BERKAS, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s([;,.])/g, "$1")
    .trim();
  s = s.charAt(0).toUpperCase() + s.slice(1);
  return /[.!?]$/.test(s) ? s : `${s}.`;
}

/** Alasan risiko dari backend ("Temuan KRITIS: R06 ...") menjadi nama hal yang dimengerti. */
export function alasanSederhana(alasan: string): string {
  const m = alasan.match(/^Temuan (KRITIS|TINGGI): (\S+)/);
  if (m) return `${HAL[m[2]] ?? "Catatan"} (${TINGKAT[m[1]].toLowerCase()})`;
  if (alasan.startsWith("Ada perintah tersisip")) return "ada tulisan perintah di bukti";
  if (alasan.startsWith("Total diajukan lebih dari")) return alasan.replace("Total diajukan lebih dari", "total di atas");
  return alasan.replace("Pemeriksaan backend:", "Pemeriksaan sistem:");
}

export const NAMA_BERKAS: Record<string, string> = {
  "draf_spj.docx": "Draf SPJ (Word)",
  "rekap.xlsx": "Rekap biaya (Excel)",
  "layar_konfirmasi.html": "Ringkasan pemeriksaan",
  "timeline.json": "Kronologi perjalanan (data)",
  "manifest.json": "Daftar berkas (data)",
};
