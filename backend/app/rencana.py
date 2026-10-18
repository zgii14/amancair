from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app import audit, rules
from app.db import iso
from app.profil import Kontak, Profil, Sifat

BATAS_PENERIMA_NORMAL = 3


class Asal(str, Enum):
    PIMPINAN = "pimpinan"
    SURAT = "surat"
    DIREKTORI = "direktori"


class Nilai(BaseModel):
    nilai: str
    asal: Asal


class Aksi(BaseModel):
    jenis: Literal["email", "jadwal", "tugas", "disposisi"]
    penerima: list[Nilai] = Field(min_length=1)
    judul: str
    isi: Nilai
    waktu_mulai: Nilai | None = None
    durasi_menit: int = 60
    instruksi: str | None = None
    tenggat: str | None = None


class SuratTerstruktur(BaseModel):
    input_asli: str
    ringkasan: str
    pengirim: str | None = None
    perihal: str | None = None
    sifat: Sifat = "biasa"
    perintah_tersisip: list[str] = []
    kutipan_sumber: list[str] = []


class Rencana(BaseModel):
    pengaju: str
    surat: SuratTerstruktur
    aksi: list[Aksi] = Field(min_length=1)
    catatan_checker: list[str] = []


class HasilAjukan(BaseModel):
    ok: bool
    rencana_id: str | None = None
    hash: str | None = None
    risiko: str | None = None
    alasan_risiko: list[str] = []
    pelanggaran: list[dict] = []
    peringatan: list[str] = []
    saran_waktu: list[str] = []


@dataclass(frozen=True)
class PenerimaTerurai:
    nilai: str
    email: str
    kontak: Kontak | None
    eksternal: bool


def hash_rencana(r: Rencana) -> str:
    data = json.dumps(r.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def urai_penerima(profil: Profil, nilai: str) -> PenerimaTerurai | None:
    k = profil.kontak_by_id(nilai) or (profil.kontak_by_email(nilai) if "@" in nilai else None)
    if k:
        return PenerimaTerurai(nilai, k.email, k, False)
    if "@" in nilai:
        email = nilai.strip().lower()
        internal = any(email.endswith("@" + d.lower()) for d in profil.domain_email)
        return PenerimaTerurai(nilai, email, None, not internal)
    return None


def nilai_risiko(per_aksi: list[list[PenerimaTerurai]]) -> tuple[str, list[str]]:
    alasan: list[str] = []
    for i, ps in enumerate(per_aksi, 1):
        for p in ps:
            if p.eksternal:
                alasan.append(f"Aksi {i}: penerima eksternal {p.email}")
        if len({p.email for p in ps}) > BATAS_PENERIMA_NORMAL:
            alasan.append(f"Aksi {i}: lebih dari {BATAS_PENERIMA_NORMAL} penerima")
    return ("tinggi" if alasan else "normal"), alasan


def _p(kode: str, pesan: str) -> dict:
    return {"kode": kode, "pesan": pesan}


def _cek_jadwal(profil: Profil, a: Aksi, uraian: list[PenerimaTerurai], pengaju: Kontak | None, i: int) -> tuple[list[dict], list[str]]:
    if a.waktu_mulai is None:
        return [_p("WAKTU_KOSONG", f"Aksi {i}: jadwal tanpa waktu.")], []
    try:
        mulai = datetime.fromisoformat(a.waktu_mulai.nilai)
    except ValueError:
        return [_p("WAKTU_TIDAK_VALID", f"Aksi {i}: waktu '{a.waktu_mulai.nilai}' tidak valid (pakai ISO 8601 dengan zona).")], []
    zona = [u.kontak.zona for u in uraian if u.kontak] + ([pengaju.zona] if pengaju else [])
    pel = rules.cek_waktu_rapat(profil, mulai, a.durasi_menit, zona)
    if not pel:
        return [], []
    saran = [s.isoformat() for s in rules.saran_slot(profil, mulai, a.durasi_menit, zona)]
    return [_p(p.kode, f"Aksi {i}: {p.pesan}") for p in pel], saran


def _cek_disposisi(profil: Profil, a: Aksi, uraian: list[PenerimaTerurai], pengaju_id: str, i: int) -> list[dict]:
    if not a.instruksi:
        return [_p("INSTRUKSI_KOSONG", f"Aksi {i}: disposisi tanpa instruksi.")]
    hasil: list[dict] = []
    for u in uraian:
        if u.kontak is None:
            hasil.append(_p("DISPOSISI_EKSTERNAL", f"Aksi {i}: disposisi hanya untuk pegawai internal, bukan {u.email}."))
            continue
        hasil += [_p(p.kode, f"Aksi {i}: {p.pesan}") for p in rules.cek_disposisi(profil, pengaju_id, u.kontak.id, a.instruksi)]
    return hasil


def ajukan(conn: sqlite3.Connection, profil: Profil, rencana: Rencana, now: datetime) -> HasilAjukan:
    pelanggaran: list[dict] = []
    peringatan: list[str] = []
    saran: list[str] = []
    pengaju = profil.kontak_by_id(rencana.pengaju)
    if pengaju is None:
        pelanggaran.append(_p("PENGAJU_TIDAK_DIKENAL", f"Pengaju '{rencana.pengaju}' tidak ada di direktori."))

    per_aksi: list[list[PenerimaTerurai]] = []
    for i, a in enumerate(rencana.aksi, 1):
        uraian: list[PenerimaTerurai] = []
        for p in a.penerima:
            u = urai_penerima(profil, p.nilai)
            if u is None:
                pelanggaran.append(_p("PENERIMA_TIDAK_DIKENAL", f"Aksi {i}: '{p.nilai}' tidak ada di direktori dan bukan alamat email."))
                continue
            uraian.append(u)
            if p.asal is Asal.SURAT:
                peringatan.append(f"Aksi {i}: penerima '{p.nilai}' hanya berasal dari isi surat, bukan instruksi pimpinan.")
        per_aksi.append(uraian)
        if a.jenis == "jadwal":
            pel, sar = _cek_jadwal(profil, a, uraian, pengaju, i)
            pelanggaran += pel
            saran += sar
        elif a.jenis == "disposisi":
            pelanggaran += _cek_disposisi(profil, a, uraian, rencana.pengaju, i)

    if rencana.surat.perintah_tersisip:
        peringatan.append("Terdeteksi perintah tersisip di dokumen dan diabaikan: " + "; ".join(rencana.surat.perintah_tersisip))
    risiko, alasan = nilai_risiko(per_aksi)

    if pelanggaran:
        with conn:
            audit.catat(conn, rencana.pengaju, "rencana_ditolak_aturan", {"pelanggaran": pelanggaran}, now)
        return HasilAjukan(ok=False, pelanggaran=pelanggaran, peringatan=peringatan, saran_waktu=saran)

    rid = uuid.uuid4().hex[:12]
    h = hash_rencana(rencana)
    data = rencana.model_dump(mode="json")
    with conn:
        conn.execute(
            "INSERT INTO rencana (id, pengaju, surat_json, aksi_json, catatan_checker_json, hash, status, risiko,"
            " alasan_risiko_json, peringatan_json, dibuat) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                rid, rencana.pengaju,
                json.dumps(data["surat"], ensure_ascii=False),
                json.dumps(data["aksi"], ensure_ascii=False),
                json.dumps(data["catatan_checker"], ensure_ascii=False),
                h, "PENDING", risiko,
                json.dumps(alasan, ensure_ascii=False),
                json.dumps(peringatan, ensure_ascii=False),
                iso(now),
            ),
        )
        audit.catat(conn, rencana.pengaju, "rencana_diajukan", {"rencana_id": rid, "hash": h, "risiko": risiko}, now)
    return HasilAjukan(ok=True, rencana_id=rid, hash=h, risiko=risiko, alasan_risiko=alasan, peringatan=peringatan)


def _baris(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "pengaju": r["pengaju"],
        "surat": json.loads(r["surat_json"]),
        "aksi": json.loads(r["aksi_json"]),
        "catatan_checker": json.loads(r["catatan_checker_json"]),
        "hash": r["hash"],
        "status": r["status"],
        "risiko": r["risiko"],
        "alasan_risiko": json.loads(r["alasan_risiko_json"]),
        "peringatan": json.loads(r["peringatan_json"]),
        "dibuat": r["dibuat"],
    }


def ambil(conn: sqlite3.Connection, rencana_id: str) -> dict | None:
    r = conn.execute("SELECT * FROM rencana WHERE id=?", (rencana_id,)).fetchone()
    return _baris(r) if r else None


def daftar(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status:
        rows = conn.execute("SELECT * FROM rencana WHERE status=? ORDER BY dibuat DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM rencana ORDER BY dibuat DESC").fetchall()
    return [_baris(r) for r in rows]


def rencana_dari_baris(d: dict) -> Rencana:
    return Rencana(pengaju=d["pengaju"], surat=d["surat"], aksi=d["aksi"], catatan_checker=d["catatan_checker"])


def ubah_status(conn: sqlite3.Connection, rencana_id: str, status: str) -> None:
    conn.execute("UPDATE rencana SET status=? WHERE id=?", (status, rencana_id))
