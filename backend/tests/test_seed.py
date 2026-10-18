from datetime import datetime, timezone

import pytest

from app import tools
from app.db import buka
from app.profil import muat_profil
from app.rencana import ajukan
from scripts.seed_demo import SKENARIO
from tests.conftest import PROFIL_DIR

# Senin, Kamis, Jumat, Sabtu: helper tanggal di seed harus selalu menghasilkan waktu valid.
REF = [
    datetime(2026, 10, 19, 1, 0, tzinfo=timezone.utc),
    datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc),
    datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc),
    datetime(2026, 10, 24, 3, 0, tzinfo=timezone.utc),
]


@pytest.mark.parametrize("ref", REF)
@pytest.mark.parametrize("pid", list(SKENARIO))
def test_semua_skenario_lolos_aturan(pid, ref):
    profil = muat_profil(PROFIL_DIR / f"{pid}.yaml")
    conn = buka(":memory:")
    for r in SKENARIO[pid](ref):
        h = ajukan(conn, profil, r, ref)
        assert h.ok, (r.surat.perihal, h.pelanggaran)


def test_kecamatan_punya_dua_budi(now):
    profil = muat_profil(PROFIL_DIR / "kecamatan.yaml")
    ktx = tools.Konteks(profil=profil, conn=buka(":memory:"), user_id="camat_andi", jam=lambda: now)
    hasil = tools.cari_kontak(ktx, "budi")
    assert {h["jabatan"] for h in hasil} == {"Kasi Pemerintahan", "Kasi Ketenteraman dan Ketertiban Umum"}


def test_kecamatan_skenario_menunjukkan_fitur_kunci():
    rencana = SKENARIO["kecamatan"](REF[0])
    assert any(r.surat.perintah_tersisip for r in rencana)
    assert any(r.surat.sifat == "rahasia" for r in rencana)
    assert any(a.jenis == "jadwal" for r in rencana for a in r.aksi)
    assert any(p.asal.value == "surat" for r in rencana for a in r.aksi for p in a.penerima)
