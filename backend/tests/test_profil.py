import pytest

from app.profil import Profil, muat_profil
from tests.conftest import PROFIL_DIR


@pytest.mark.parametrize("nama", ["perusahaan", "kecamatan"])
def test_profil_valid(nama):
    p = muat_profil(PROFIL_DIR / f"{nama}.yaml")
    assert p.id == nama
    assert any(j.boleh_menyetujui for j in p.jabatan)
    assert "Hadiri dan laporkan" in p.instruksi_disposisi


def test_perusahaan_punya_dua_budi(profil):
    assert len([k for k in profil.kontak if k.nama.startswith("Budi")]) == 2


def test_lookup(profil):
    assert profil.kontak_by_id("budi_s").zona == "WIB"
    assert profil.kontak_by_email("BUDI.HARTONO@nusantaralogistik.example").id == "budi_h"
    assert profil.jabatan_kontak("rina").boleh_menyetujui is True
    assert profil.kontak_by_id("tidak_ada") is None


def test_jabatan_kontak_harus_ada():
    with pytest.raises(ValueError):
        Profil.model_validate({
            "id": "x", "nama_org": "X", "domain_email": ["x.example"],
            "jabatan": [{"id": "a", "nama": "A", "level": 1, "unit": "U"}],
            "kontak": [{"id": "k", "nama": "K", "jabatan": "zzz", "email": "k@x.example", "zona": "WIB"}],
            "instruksi_disposisi": ["Setuju"],
        })
