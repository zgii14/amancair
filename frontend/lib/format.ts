const ZONA_OFFSET: Record<string, { label: string; tz: string }> = {
  "+07:00": { label: "WIB", tz: "Asia/Jakarta" },
  "+08:00": { label: "WITA", tz: "Asia/Makassar" },
  "+09:00": { label: "WIT", tz: "Asia/Jayapura" },
};

/** Waktu rapat ditampilkan pada zona yang tertulis di rencana, bukan zona browser. */
export function waktuRapat(iso: string): string {
  const offset = iso.slice(-6);
  const zona = ZONA_OFFSET[offset] ?? { label: offset, tz: "Asia/Jakarta" };
  const d = new Date(iso);
  const tanggal = new Intl.DateTimeFormat("id-ID", {
    weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: zona.tz,
  }).format(d);
  const jam = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: zona.tz }).format(d);
  return `${tanggal}, ${jam} ${zona.label}`;
}

export function waktuLokal(iso: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(iso));
}

export function tanggal(isoDate: string): string {
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${isoDate.slice(0, 10)}T12:00:00`));
}

export const JENIS_AKSI: Record<string, string> = {
  email: "Kirim email",
  jadwal: "Jadwalkan rapat",
  tugas: "Buat tugas",
  disposisi: "Disposisi",
};

export const SIFAT: Record<string, string> = { biasa: "Biasa", segera: "Segera", rahasia: "Rahasia" };
