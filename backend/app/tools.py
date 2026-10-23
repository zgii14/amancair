"""Logika tool MCP. Hanya baca + ajukan; tidak ada fungsi kirim/jadwal/ubah di sini."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from app import rules, spj
from app import rencana as rencana_mod
from app.profil import Jabatan, Profil


@dataclass
class Konteks:
    profil: Profil
    conn: sqlite3.Connection
    user_id: str
    jam: Callable[[], datetime]
    spj_draf: Path | None = None


def _jabatan_user(ktx: Konteks) -> Jabatan:
    j = ktx.profil.jabatan_kontak(ktx.user_id)
    if j is None:
        raise ValueError(f"user '{ktx.user_id}' tidak ada di profil")
    return j


def _waktu(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("Sertakan zona waktu, mis. 2026-10-23T08:00:00+07:00")
    return dt


def cari_kontak(ktx: Konteks, kata: str) -> list[dict]:
    q = kata.strip().lower()
    hasil = []
    for k in ktx.profil.kontak:
        j = ktx.profil.jabatan_by_id(k.jabatan)
        if q in f"{k.id} {k.nama} {j.nama} {j.unit}".lower():
            hasil.append({"id": k.id, "nama": k.nama, "jabatan": j.nama, "unit": j.unit, "email": k.email, "zona": k.zona})
    return hasil


def cek_kalender(ktx: Konteks, kontak_id: str, dari: str, sampai: str) -> list[dict]:
    d, s = _waktu(dari), _waktu(sampai)
    boleh = set(_jabatan_user(ktx).sifat_boleh)
    hasil = []
    for a in ktx.profil.kalender:
        if kontak_id in a.peserta and a.mulai < s and a.selesai > d:
            judul = a.judul if a.sifat in boleh else "Sibuk"
            hasil.append({"judul": judul, "mulai": a.mulai.isoformat(), "selesai": a.selesai.isoformat()})
    return hasil


def cek_aturan(ktx: Konteks, mulai: str, durasi_menit: int, peserta: list[str]) -> dict:
    m = _waktu(mulai)
    zona, tidak_dikenal = [], []
    for pid in [*peserta, ktx.user_id]:
        k = ktx.profil.kontak_by_id(pid)
        if k:
            zona.append(k.zona)
        else:
            tidak_dikenal.append(pid)
    pel = rules.cek_waktu_rapat(ktx.profil, m, durasi_menit, zona)
    saran = [x.isoformat() for x in rules.saran_slot(ktx.profil, m, durasi_menit, zona)] if pel else []
    return {
        "lolos": not pel,
        "pelanggaran": [{"kode": p.kode, "pesan": p.pesan} for p in pel],
        "saran": saran,
        "peserta_tidak_dikenal": tidak_dikenal,
    }


def profil_org(ktx: Konteks) -> dict:
    p = ktx.profil
    k = p.kontak_by_id(ktx.user_id)
    return {
        "nama_org": p.nama_org,
        "jabatan": [{"id": j.id, "nama": j.nama, "level": j.level, "unit": j.unit} for j in p.jabatan],
        "instruksi_disposisi": p.instruksi_disposisi,
        "jam_kerja": {"mulai": f"{p.aturan.jam_kerja.mulai:%H:%M}", "selesai": f"{p.aturan.jam_kerja.selesai:%H:%M}"},
        "jumatan": {"mulai": f"{p.aturan.jumatan.mulai:%H:%M}", "selesai": f"{p.aturan.jumatan.selesai:%H:%M}"},
        "user_aktif": {"id": k.id, "nama": k.nama, "jabatan": _jabatan_user(ktx).nama} if k else None,
    }


def ajukan_rencana(ktx: Konteks, rencana: rencana_mod.Rencana) -> dict:
    r = rencana.model_copy(update={"pengaju": ktx.user_id})
    return rencana_mod.ajukan(ktx.conn, ktx.profil, r, ktx.jam()).model_dump()


def ajukan_spj(ktx: Konteks, pengajuan: spj.PengajuanSPJ) -> dict:
    if ktx.spj_draf is None:
        return {"ok": False, "error": "Gerbang SPJ tidak aktif untuk profil ini"}
    try:
        r = spj.ajukan(ktx.conn, ktx.spj_draf, pengajuan, ktx.user_id, ktx.jam())
    except spj.SPJError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "nomor": r["nomor"], "versi": r["versi"], "risiko": r["risiko"], "manifest_hash": r["manifest_hash"],
            "jumlah_berkas": len(r["manifest"]),
            "pesan": "Diajukan ke Meja Pimpinan. BELUM dicairkan; menunggu keputusan bendahara."}
