from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

Zona = Literal["WIB", "WITA", "WIT"]
Sifat = Literal["biasa", "segera", "rahasia"]


class Jabatan(BaseModel):
    id: str
    nama: str
    level: int  # 1 = tertinggi
    unit: str
    boleh_menyetujui: bool = False
    sifat_boleh: list[Sifat] = ["biasa", "segera"]


class Kontak(BaseModel):
    id: str
    nama: str
    jabatan: str
    email: str
    zona: Zona


class JamKerja(BaseModel):
    mulai: time = time(8, 0)
    selesai: time = time(16, 0)


class Jumatan(BaseModel):
    mulai: time = time(11, 30)
    selesai: time = time(13, 0)


class Aturan(BaseModel):
    jam_kerja: JamKerja = JamKerja()
    jumatan: Jumatan = Jumatan()
    libur: list[date] = []


class AcaraKalender(BaseModel):
    id: str
    judul: str
    peserta: list[str]
    mulai: datetime
    selesai: datetime
    sifat: Sifat = "biasa"


class Profil(BaseModel):
    id: str
    nama_org: str
    domain_email: list[str]
    jabatan: list[Jabatan]
    kontak: list[Kontak]
    aturan: Aturan = Aturan()
    instruksi_disposisi: list[str]
    kalender: list[AcaraKalender] = []

    @model_validator(mode="after")
    def _cek_referensi(self) -> "Profil":
        ids = {j.id for j in self.jabatan}
        for k in self.kontak:
            if k.jabatan not in ids:
                raise ValueError(f"kontak {k.id}: jabatan '{k.jabatan}' tidak ada")
        return self

    def kontak_by_id(self, kontak_id: str) -> Kontak | None:
        return next((k for k in self.kontak if k.id == kontak_id), None)

    def kontak_by_email(self, email: str) -> Kontak | None:
        e = email.strip().lower()
        return next((k for k in self.kontak if k.email.lower() == e), None)

    def jabatan_by_id(self, jabatan_id: str) -> Jabatan | None:
        return next((j for j in self.jabatan if j.id == jabatan_id), None)

    def jabatan_kontak(self, kontak_id: str) -> Jabatan | None:
        k = self.kontak_by_id(kontak_id)
        return self.jabatan_by_id(k.jabatan) if k else None


def muat_profil(path: Path) -> Profil:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Profil.model_validate(data)
