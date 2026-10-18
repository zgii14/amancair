"""Lapis otomatis testcases/kasus.yaml ikut dijalankan pytest agar regresi langsung ketahuan."""
import pytest

from scripts.jalankan_test import CEK, jalankan_otomatis, muat_kasus

KASUS = muat_kasus()
OTOMATIS = [k for k in KASUS if k.get("otomatis")]


def test_id_unik_dan_minimal_20_kasus():
    ids = [k["id"] for k in KASUS]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 20


def test_semua_aturan_accountability_tercakup():
    aturan = {a for k in KASUS for a in k["aturan"]}
    assert aturan == {"SOURCES", "PERMISSIONS", "APPROVAL", "LIMITS", "RECORD"}


def test_jenis_cek_dikenal():
    assert {k["otomatis"]["cek"] for k in OTOMATIS} <= set(CEK)


@pytest.mark.parametrize("kasus", OTOMATIS, ids=[k["id"] for k in OTOMATIS])
def test_lapis_sistem(kasus):
    status, catatan = jalankan_otomatis(kasus)
    assert status == "PASS", catatan
