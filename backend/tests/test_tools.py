import pytest

from app import tools
from app.rencana import ambil
from tests.factories import rencana_email


def test_cari_budi_dua_hasil(ktx):
    hasil = tools.cari_kontak(ktx, "budi")
    assert {h["id"] for h in hasil} == {"budi_s", "budi_h"}
    assert {h["zona"] for h in hasil} == {"WIB", "WITA"}


def test_cari_berdasarkan_jabatan(ktx):
    assert [h["id"] for h in tools.cari_kontak(ktx, "staf keuangan")] == ["sari"]


def test_kalender_rahasia_disamarkan_untuk_yang_tidak_berhak(ktx):
    ktx.user_id = "budi_s"
    hasil = tools.cek_kalender(ktx, "rina", "2026-10-22T00:00:00+07:00", "2026-10-23T00:00:00+07:00")
    assert [h["judul"] for h in hasil] == ["Sibuk"]


def test_kalender_rahasia_terlihat_untuk_yang_berhak(ktx):
    hasil = tools.cek_kalender(ktx, "rina", "2026-10-22T00:00:00+07:00", "2026-10-23T00:00:00+07:00")
    assert [h["judul"] for h in hasil] == ["Rapat restrukturisasi direksi"]


def test_kalender_tanpa_zona_ditolak(ktx):
    with pytest.raises(ValueError):
        tools.cek_kalender(ktx, "rina", "2026-10-22T00:00:00", "2026-10-23T00:00:00")


def test_cek_aturan_jumatan(ktx):
    hasil = tools.cek_aturan(ktx, "2026-10-23T12:00:00+07:00", 60, ["budi_s"])
    assert hasil["lolos"] is False
    assert hasil["saran"][0] == "2026-10-23T13:00:00+07:00"


def test_cek_aturan_peserta_tidak_dikenal(ktx):
    hasil = tools.cek_aturan(ktx, "2026-10-21T10:00:00+07:00", 60, ["hantu"])
    assert hasil["peserta_tidak_dikenal"] == ["hantu"]


def test_profil_org(ktx):
    p = tools.profil_org(ktx)
    assert "Hadiri dan laporkan" in p["instruksi_disposisi"]
    assert p["user_aktif"]["id"] == "rina"


def test_ajukan_memaksa_pengaju_user_aktif(ktx):
    hasil = tools.ajukan_rencana(ktx, rencana_email(pengaju="budi_s"))
    assert hasil["ok"] is True
    assert ambil(ktx.conn, hasil["rencana_id"])["pengaju"] == "rina"
