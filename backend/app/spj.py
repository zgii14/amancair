"""Gerbang persetujuan SPJ: agen mengajukan draf, backend menghitung sidik, bendahara menyetujui, backend mencairkan.

Agen tidak pernah menulis ke folder siap-cair. Sidik (manifest) dihitung backend sendiri saat pengajuan dan dihitung
ulang saat persetujuan; file yang berubah, bertambah, atau hilang membatalkan pencairan.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app import audit
from app.db import iso

BATAS_TOTAL_RISIKO = 10_000_000
LEVEL_TINGGI = {"KRITIS", "TINGGI"}
URUTAN_LEVEL = {"KRITIS": 0, "TINGGI": 1, "SEDANG": 2, "RENDAH": 3}


class SPJError(Exception):
    pass


class Temuan(BaseModel):
    level: Literal["KRITIS", "TINGGI", "SEDANG", "RENDAH"]
    aturan: str
    deskripsi: str
    sumber: str | None = None


class PengajuanSPJ(BaseModel):
    nomor: str = Field(pattern=r"^SPJ-\d{4}-\d{3}[a-z]?$")
    pegawai: str
    tujuan: str
    tanggal_spt: str
    total_diajukan: int = Field(ge=0)
    total_dibayar: int = Field(ge=0)
    temuan: list[Temuan] = []
    perintah_tersisip: list[str] = []
    # Diisi backend saat diajukan (selisih dengan periksa_aturan); isian dari agen diabaikan.
    catatan_backend: list[str] = []


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hitung_manifest(folder: Path) -> dict[str, str]:
    return {f.relative_to(folder).as_posix(): _sha(f) for f in sorted(folder.rglob("*")) if f.is_file()}


def hash_manifest(m: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(m, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _risiko(p: PengajuanSPJ) -> tuple[str, list[str]]:
    alasan = [f"Pemeriksaan backend: {c}" for c in p.catatan_backend]
    alasan += [f"Temuan {t.level}: {t.aturan} {t.deskripsi}" for t in p.temuan if t.level in LEVEL_TINGGI]
    if p.perintah_tersisip:
        alasan.append("Ada perintah tersisip di dokumen")
    if p.total_diajukan > BATAS_TOTAL_RISIKO:
        alasan.append(f"Total diajukan lebih dari Rp{BATAS_TOTAL_RISIKO:,}".replace(",", "."))
    return ("tinggi" if alasan else "normal"), alasan


def _baris(r: sqlite3.Row) -> dict:
    data = json.loads(r["data_json"])
    data["temuan"] = sorted(data.get("temuan", []), key=lambda t: URUTAN_LEVEL[t["level"]])
    return {**data, "pengaju": r["pengaju"], "manifest": json.loads(r["manifest_json"]), "manifest_hash": r["manifest_hash"],
            "risiko": r["risiko"], "alasan_risiko": _risiko(PengajuanSPJ(**json.loads(r["data_json"])))[1],
            "status": r["status"], "versi": r["versi"], "diajukan": r["diajukan"],
            "diputuskan_oleh": r["diputuskan_oleh"], "alasan": r["alasan"]}


def ambil(conn: sqlite3.Connection, nomor: str) -> dict | None:
    r = conn.execute("SELECT * FROM spj WHERE nomor=?", (nomor,)).fetchone()
    return _baris(r) if r else None


def daftar(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    q, args = "SELECT * FROM spj", ()
    if status:
        q, args = q + " WHERE status=?", (status,)
    return [_baris(r) for r in conn.execute(q + " ORDER BY diajukan DESC", args)]


def path_berkas(draf_root: Path, nomor: str, relatif: str) -> Path:
    folder = (draf_root / nomor).resolve()
    p = (folder / relatif).resolve()
    if folder not in p.parents or not p.is_file():
        raise SPJError("Berkas tidak ditemukan")
    return p


def ajukan(conn: sqlite3.Connection, draf_root: Path, p: PengajuanSPJ, pengaju: str, now: datetime,
           wajib_periksa: bool = False) -> dict:
    """wajib_periksa: bandingkan dengan hasil periksa_aturan (dipakai jalur MCP; seed demo tidak)."""
    from app import aturan_spj

    catatan = []
    if wajib_periksa:
        catatan = aturan_spj.selisih_dengan_pengajuan(aturan_spj.ambil_pemeriksaan(conn, p.nomor), p.total_dibayar,
                                                      {t.aturan for t in p.temuan})
    p = p.model_copy(update={"catatan_backend": catatan})
    folder = draf_root / p.nomor
    if not (folder / "rekap.xlsx").is_file():
        raise SPJError(f"Folder draf {p.nomor} atau rekap.xlsx tidak ditemukan")
    lama = ambil(conn, p.nomor)
    if lama and lama["status"] in ("DICAIRKAN",):
        raise SPJError(f"{p.nomor} sudah dicairkan; tidak bisa diajukan ulang")
    m = hitung_manifest(folder)
    h = hash_manifest(m)
    risiko, _ = _risiko(p)
    versi = (lama["versi"] + 1) if lama else 1
    with conn:
        conn.execute(
            "INSERT INTO spj (nomor, pengaju, data_json, manifest_json, manifest_hash, risiko, status, versi, diajukan)"
            " VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(nomor) DO UPDATE SET pengaju=excluded.pengaju, data_json=excluded.data_json,"
            " manifest_json=excluded.manifest_json, manifest_hash=excluded.manifest_hash, risiko=excluded.risiko,"
            " status='PENDING', versi=excluded.versi, diajukan=excluded.diajukan, diputuskan_oleh=NULL, alasan=NULL",
            (p.nomor, pengaju, p.model_dump_json(), json.dumps(m), h, risiko, "PENDING", versi, iso(now)),
        )
        audit.catat(conn, pengaju, "spj_diajukan",
                    {"nomor": p.nomor, "versi": versi, "manifest_hash": h, "jumlah_berkas": len(m), "risiko": risiko}, now)
    return ambil(conn, p.nomor)


NOMOR_SPJ = re.compile(r"^SPJ-\d{4}-\d{3}[a-z]?$")


def _path_draf(draf_root: Path, nomor: str, relatif: str) -> Path:
    if not NOMOR_SPJ.match(nomor):
        raise SPJError("Nomor SPJ tidak valid")
    folder = (draf_root / nomor).resolve()
    p = (folder / relatif).resolve()
    if folder not in p.parents:
        raise SPJError("Path berkas tidak valid")
    return p


def sinkron_draf(draf_root: Path, nomor: str, manifest_lokal: dict[str, str]) -> list[str]:
    """Samakan folder draf di server dengan laptop WorkBuddy.

    Berkas yang tidak ada di laptop dihapus; yang kembalikan adalah daftar berkas yang perlu diunggah.
    """
    for rel in [*manifest_lokal, "rekap.xlsx"]:
        _path_draf(draf_root, nomor, rel)
    folder = draf_root / nomor
    server = hitung_manifest(folder) if folder.is_dir() else {}
    for rel in set(server) - set(manifest_lokal):
        (folder / rel).unlink()
    return sorted(rel for rel, h in manifest_lokal.items() if server.get(rel) != h)


def tulis_draf(draf_root: Path, nomor: str, relatif: str, data: bytes) -> None:
    p = _path_draf(draf_root, nomor, relatif)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def seed(conn: sqlite3.Connection, draf_root: Path, berkas: Path, now: datetime) -> list[str]:
    """Ajukan SPJ contoh untuk demo online. Yang sudah ada di database dilewati."""
    data = json.loads(berkas.read_text(encoding="utf-8"))
    baru = []
    for item in data["pengajuan"]:
        p = PengajuanSPJ(**item)
        if ambil(conn, p.nomor) is None:
            ajukan(conn, draf_root, p, data["pengaju"], now)
            baru.append(p.nomor)
    return baru


def setujui(conn: sqlite3.Connection, draf_root: Path, siap_root: Path, nomor: str, oleh: str,
            konfirmasi_risiko: bool, now: datetime) -> dict:
    r = ambil(conn, nomor)
    if r is None:
        raise SPJError("SPJ tidak ditemukan")
    if r["status"] != "PENDING":
        raise SPJError(f"SPJ berstatus {r['status']}")
    if r["risiko"] == "tinggi" and not konfirmasi_risiko:
        raise SPJError("Risiko tinggi: perlu konfirmasi tambahan bendahara")
    sekarang = hitung_manifest(draf_root / nomor)
    if hash_manifest(sekarang) != r["manifest_hash"]:
        beda = sorted(set(sekarang.items()) ^ set(r["manifest"].items()))
        with conn:
            audit.catat(conn, oleh, "spj_pencairan_ditolak",
                        {"nomor": nomor, "alasan": "berkas berubah sejak diajukan", "berkas": sorted({k for k, _ in beda})}, now)
        raise SPJError("Berkas berubah sejak diajukan; minta agen mengajukan ulang")
    tujuan = siap_root / nomor
    if tujuan.exists():
        raise SPJError("Folder siap-cair sudah ada")
    tujuan.mkdir(parents=True)
    for rel in r["manifest"]:
        (tujuan / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(draf_root / nomor / rel, tujuan / rel)
    if hitung_manifest(tujuan) != r["manifest"]:
        shutil.rmtree(tujuan)
        with conn:
            audit.catat(conn, oleh, "spj_pencairan_ditolak", {"nomor": nomor, "alasan": "salinan tidak identik"}, now)
        raise SPJError("Salinan tidak identik; pencairan dibatalkan")
    with conn:
        conn.execute("UPDATE spj SET status='DICAIRKAN', diputuskan_oleh=? WHERE nomor=?", (oleh, nomor))
        audit.catat(conn, oleh, "spj_dicairkan",
                    {"nomor": nomor, "versi": r["versi"], "manifest_hash": r["manifest_hash"], "total_dibayar": r["total_dibayar"]}, now)
    return ambil(conn, nomor)


def tolak(conn: sqlite3.Connection, nomor: str, oleh: str, alasan: str, now: datetime) -> dict:
    r = ambil(conn, nomor)
    if r is None:
        raise SPJError("SPJ tidak ditemukan")
    if r["status"] != "PENDING":
        raise SPJError(f"SPJ berstatus {r['status']}")
    with conn:
        conn.execute("UPDATE spj SET status='DITOLAK', diputuskan_oleh=?, alasan=? WHERE nomor=?", (oleh, alasan, nomor))
        audit.catat(conn, oleh, "spj_ditolak", {"nomor": nomor, "versi": r["versi"], "alasan": alasan}, now)
    return ambil(conn, nomor)
