export type Asal = "pimpinan" | "surat" | "direktori";
export type Nilai = { nilai: string; asal: Asal };
export type JenisAksi = "email" | "jadwal" | "tugas" | "disposisi";

export type Aksi = {
  jenis: JenisAksi;
  penerima: Nilai[];
  judul: string;
  isi: Nilai;
  waktu_mulai: Nilai | null;
  durasi_menit: number;
  instruksi: string | null;
  tenggat: string | null;
};

export type Surat = {
  input_asli: string;
  ringkasan: string;
  pengirim: string | null;
  perihal: string | null;
  sifat: "biasa" | "segera" | "rahasia";
  perintah_tersisip: string[];
  kutipan_sumber: string[];
};

export type Status = "PENDING" | "DISETUJUI" | "DIEKSEKUSI" | "DITOLAK" | "DIBATALKAN";

export type Rencana = {
  id: string;
  pengaju: string;
  surat: Surat;
  aksi: Aksi[];
  catatan_checker: string[];
  hash: string;
  status: Status;
  risiko: "normal" | "tinggi";
  alasan_risiko: string[];
  peringatan: string[];
  dibuat: string;
};

export type Me = { nama: string; jabatan: string; boleh_menyetujui: boolean; profil: string };
export type Kontak = { id: string; nama: string; jabatan: string; email: string; zona: string };
export type ProfilOrg = { nama_org: string; instruksi_disposisi: string[]; kontak: Kontak[] };

export type Terkirim = { id: number; outbox_id: number; jenis: JenisAksi; payload: Aksi; waktu: string };
export type CatatanAudit = {
  seq: number;
  waktu: string;
  aktor: string;
  kejadian: string;
  payload: Record<string, unknown>;
  hash: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "same-origin",
    cache: "no-store",
  });
  if (res.status === 401 && path !== "/login") {
    window.location.href = "/login";
    throw new ApiError(401, "Sesi berakhir, silakan masuk lagi.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Permintaan gagal (${res.status}).`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export function post<T>(path: string, data?: unknown): Promise<T> {
  return api<T>(path, { method: "POST", body: JSON.stringify(data ?? {}) });
}
