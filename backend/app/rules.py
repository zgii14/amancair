from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.profil import Profil

ZONA_TZ: dict[str, ZoneInfo] = {
    "WIB": ZoneInfo("Asia/Jakarta"),
    "WITA": ZoneInfo("Asia/Makassar"),
    "WIT": ZoneInfo("Asia/Jayapura"),
}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
LANGKAH_SLOT = timedelta(minutes=30)
BATAS_CARI = timedelta(days=7)


@dataclass(frozen=True)
class Pelanggaran:
    kode: str
    pesan: str


def _fmt(dt: datetime, zona: str) -> str:
    return f"{HARI[dt.weekday()]} {dt:%d-%m-%Y %H:%M} {zona}"


def cek_waktu_rapat(profil: Profil, mulai: datetime, durasi_menit: int, zona_peserta: list[str]) -> list[Pelanggaran]:
    if mulai.tzinfo is None:
        return [Pelanggaran("WAKTU_TANPA_ZONA", "Waktu harus menyertakan zona, mis. +07:00.")]
    selesai = mulai + timedelta(minutes=durasi_menit)
    aturan = profil.aturan
    hasil: list[Pelanggaran] = []

    def tambah(p: Pelanggaran) -> None:
        if p not in hasil:
            hasil.append(p)

    for zona in sorted(set(zona_peserta)):
        tz = ZONA_TZ[zona]
        m, s = mulai.astimezone(tz), selesai.astimezone(tz)
        if m.weekday() >= 5:
            tambah(Pelanggaran("AKHIR_PEKAN", f"{_fmt(m, zona)} jatuh di akhir pekan."))
        if m.date() in aturan.libur:
            tambah(Pelanggaran("LIBUR", f"{m:%d-%m-%Y} adalah hari libur/cuti bersama ({zona})."))
        jk = aturan.jam_kerja
        if s.date() != m.date() or m.time() < jk.mulai or s.time() > jk.selesai:
            tambah(Pelanggaran(
                "DILUAR_JAM_KERJA",
                f"Rapat {_fmt(m, zona)}–{s:%H:%M} di luar jam kerja {jk.mulai:%H:%M}–{jk.selesai:%H:%M} {zona}.",
            ))
        if m.weekday() == 4:
            j = aturan.jumatan
            jm = datetime.combine(m.date(), j.mulai, tzinfo=tz)
            js = datetime.combine(m.date(), j.selesai, tzinfo=tz)
            if m < js and s > jm:
                tambah(Pelanggaran(
                    "JUMATAN",
                    f"Rapat {_fmt(m, zona)}–{s:%H:%M} bentrok dengan salat Jumat ({j.mulai:%H:%M}–{j.selesai:%H:%M} {zona}).",
                ))
    return hasil


def saran_slot(profil: Profil, mulai: datetime, durasi_menit: int, zona_peserta: list[str], maks: int = 3) -> list[datetime]:
    if mulai.tzinfo is None:
        return []
    kandidat = mulai.replace(minute=0 if mulai.minute < 30 else 30, second=0, microsecond=0)
    batas = mulai + BATAS_CARI
    hasil: list[datetime] = []
    while kandidat <= batas and len(hasil) < maks:
        kandidat += LANGKAH_SLOT
        if not cek_waktu_rapat(profil, kandidat, durasi_menit, zona_peserta):
            hasil.append(kandidat)
    return hasil


def cek_disposisi(profil: Profil, pengirim_id: str, penerima_id: str, instruksi: str) -> list[Pelanggaran]:
    jp = profil.jabatan_kontak(pengirim_id)
    jr = profil.jabatan_kontak(penerima_id)
    if jp is None or jr is None:
        return [Pelanggaran("HIERARKI", "Pengirim atau penerima disposisi tidak ada di struktur organisasi.")]
    hasil: list[Pelanggaran] = []
    if jr.level <= jp.level:
        hasil.append(Pelanggaran("HIERARKI", f"Disposisi hanya boleh ke jenjang di bawah: {jp.nama} → {jr.nama} tidak diizinkan."))
    baku = {i.lower() for i in profil.instruksi_disposisi}
    if instruksi.strip().lower() not in baku:
        hasil.append(Pelanggaran("INSTRUKSI_TIDAK_BAKU", f"Instruksi '{instruksi}' tidak ada di daftar instruksi disposisi baku."))
    return hasil
