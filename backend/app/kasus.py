"""Pengajuan SPJ oleh pegawai dan jejak progres tim agen.

Pegawai mengunggah bukti lewat web. Skrip jembatan di laptop WorkBuddy mengambil kasus baru,
lalu melaporkan progres dari berkas kerja agen dan log audit. Backend tidak menebak progres:
yang tampil hanya kejadian yang dilaporkan jembatan dari berkas asli.
"""
from __future__ import annotations

import base64
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app import audit
from app.db import iso

NAMA_BERKAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,80}\.(txt|pdf|jpg|jpeg|png)$", re.IGNORECASE)
BATAS_BERKAS = 5 * 1024 * 1024
NOMOR_AWAL = 11  # kasus-001..011 adalah data uji yang sudah ada di proyek WorkBuddy



class KasusError(Exception):
    pass


class Berkas(BaseModel):
    nama: str
    isi_base64: str


class PengajuanKasus(BaseModel):
    tujuan: str = Field(min_length=2, max_length=80)
    maksud: str = Field(min_length=5, max_length=300)
    tanggal_berangkat: date
    tanggal_kembali: date
    catatan: str = Field(default="", max_length=1000)
    berkas: list[Berkas] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _cek(self) -> "PengajuanKasus":
        if self.tanggal_kembali < self.tanggal_berangkat:
            raise ValueError("tanggal kembali sebelum tanggal berangkat")
        return self


class Kejadian(BaseModel):
    kasus: str = Field(pattern=r"^kasus-\d{3}[a-z]?$")
    agen: str = Field(max_length=40)
    aksi: str = Field(max_length=40)
    pesan: str = Field(default="", max_length=600)
    waktu: datetime
    kunci: str = Field(max_length=200)


def nomor_spj(kasus_id: str) -> str:
    return "SPJ-2026-" + kasus_id.removeprefix("kasus-")


def _id_baru(conn: sqlite3.Connection) -> str:
    angka = [int(r["id"][6:9]) for r in conn.execute("SELECT id FROM kasus")]
    return f"kasus-{max([NOMOR_AWAL, *angka]) + 1:03d}"


def ajukan(conn: sqlite3.Connection, root: Path, pegawai: str, nama_pegawai: str, p: PengajuanKasus,
           now: datetime) -> dict:
    nama = [b.nama for b in p.berkas]
    if len(set(nama)) != len(nama):
        raise KasusError("Nama berkas tidak boleh kembar")
    isi = {}
    for b in p.berkas:
        if not NAMA_BERKAS.match(b.nama):
            raise KasusError(f"Nama berkas tidak diizinkan: {b.nama} (pakai .txt, .pdf, .jpg, .png)")
        try:
            data = base64.b64decode(b.isi_base64, validate=True)
        except ValueError:
            raise KasusError(f"Isi berkas {b.nama} rusak")
        if len(data) > BATAS_BERKAS:
            raise KasusError(f"{b.nama} lebih dari 5 MB")
        isi[b.nama] = data
    with conn:
        kid = _id_baru(conn)
        folder = root / kid
        folder.mkdir(parents=True)
        for n, data in isi.items():
            (folder / n).write_bytes(data)
        data = {"nama_pegawai": nama_pegawai, **p.model_dump(mode="json", exclude={"berkas"})}
        conn.execute("INSERT INTO kasus VALUES (?,?,?,?,?,?,?)",
                     (kid, nomor_spj(kid), pegawai, json.dumps(data), json.dumps(nama), "DITERIMA", iso(now)))
        audit.catat(conn, pegawai, "kasus_diajukan", {"kasus": kid, "berkas": nama}, now)
    return ambil(conn, kid)


def _baris(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "nomor_spj": r["nomor_spj"], "pegawai": r["pegawai"], **json.loads(r["data_json"]),
            "berkas": json.loads(r["berkas_json"]), "status_kasus": r["status"], "dibuat": r["dibuat"]}


def ambil(conn: sqlite3.Connection, kid: str) -> dict | None:
    r = conn.execute("SELECT * FROM kasus WHERE id=?", (kid,)).fetchone()
    return _baris(r) if r else None


def daftar(conn: sqlite3.Connection, pegawai: str | None = None) -> list[dict]:
    q, args = "SELECT * FROM kasus", ()
    if pegawai:
        q, args = q + " WHERE pegawai=?", (pegawai,)
    return [_baris(r) for r in conn.execute(q + " ORDER BY dibuat DESC", args)]


def path_berkas(root: Path, kid: str, nama: str) -> Path:
    folder = (root / kid).resolve()
    p = (folder / nama).resolve()
    if p.parent != folder or not p.is_file():
        raise KasusError("Berkas tidak ditemukan")
    return p


def tandai_diambil(conn: sqlite3.Connection, kid: str, now: datetime) -> None:
    with conn:
        n = conn.execute("UPDATE kasus SET status='DIAMBIL_AGEN' WHERE id=? AND status='DITERIMA'", (kid,)).rowcount
        if n:
            catat_progres(conn, [Kejadian(kasus=kid, agen="jembatan", aksi="diambil",
                                          pesan="Bukti disalin ke folder kasus WorkBuddy", waktu=now,
                                          kunci=f"{kid}:diambil")])


def catat_progres(conn: sqlite3.Connection, kejadian: list[Kejadian]) -> int:
    baru = 0
    with conn:
        for k in kejadian:
            baru += conn.execute(
                "INSERT OR IGNORE INTO progres (kasus, agen, aksi, pesan, waktu, kunci) VALUES (?,?,?,?,?,?)",
                (k.kasus, k.agen, k.aksi, k.pesan, iso(k.waktu), k.kunci)).rowcount
    return baru


def progres(conn: sqlite3.Connection, kid: str, setelah: int = 0) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, agen, aksi, pesan, waktu FROM progres WHERE kasus=? AND id>? ORDER BY waktu, id", (kid, setelah))]


def kasus_dengan_progres(conn: sqlite3.Connection) -> list[str]:
    return [r["kasus"] for r in conn.execute("SELECT DISTINCT kasus FROM progres ORDER BY kasus")]
