import base64
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import spj
from app.api import buat_app
from app.db import buka
from app.profil import muat_profil
from app.spj import PengajuanSPJ
from tests.conftest import PROFIL_DIR

PASSWORD = "rahasia-uji"
JEMBATAN = {"Authorization": "Bearer tok-jembatan"}


def b64(teks: str) -> str:
    return base64.b64encode(teks.encode()).decode()


FORM = {"tujuan": "Makassar", "maksud": "Bimtek keamanan siber", "tanggal_berangkat": "2026-10-20",
        "tanggal_kembali": "2026-10-22", "berkas": [{"nama": "tiket_berangkat.txt", "isi_base64": b64("GA 123")},
                                                    {"nama": "invoice_hotel.txt", "isi_base64": b64("Hotel 2 malam")}]}


@pytest.fixture
def env(tmp_path, now):
    draf, siap = tmp_path / "draf", tmp_path / "siap"
    p = muat_profil(PROFIL_DIR / "diskominfo.yaml")
    conn = buka(":memory:")
    app = buat_app({"diskominfo": p}, {"diskominfo": conn}, PASSWORD, jam=lambda: now,
                   spj_dirs={"diskominfo": (draf, siap)}, kasus_root=tmp_path / "kasus",
                   jembatan=("tok-jembatan", "diskominfo"))
    return app, conn, draf, tmp_path / "kasus"


def klien(app, user):
    k = TestClient(app)
    assert k.post("/api/login", json={"profil": "diskominfo", "username": user, "password": PASSWORD}).status_code == 200
    return k


def test_pegawai_mengajukan_dan_melihat_miliknya_saja(env):
    app, _, _, root = env
    budi = klien(app, "budi_santoso")
    r = budi.post("/api/kasus", json=FORM).json()
    assert r["id"] == "kasus-012" and r["nomor_spj"] == "SPJ-2026-012" and r["status"] == "DITERIMA"
    assert (root / "kasus-012" / "tiket_berangkat.txt").read_text() == "GA 123"
    assert [k["id"] for k in budi.get("/api/kasus").json()] == ["kasus-012"]
    lestari = klien(app, "lestari")
    assert lestari.get("/api/kasus").json() == []
    assert lestari.get("/api/kasus/kasus-012").status_code == 404
    assert klien(app, "sri").get("/api/kasus/kasus-012").status_code == 200


@pytest.mark.parametrize("nama", ["../evil.txt", "skrip.sh", ".htaccess.txt"])
def test_nama_berkas_berbahaya_ditolak(env, nama):
    app, _, _, _ = env
    form = {**FORM, "berkas": [{"nama": nama, "isi_base64": b64("x")}]}
    assert klien(app, "budi_santoso").post("/api/kasus", json=form).status_code == 422


def test_jembatan_wajib_token(env):
    app, _, _, _ = env
    k = TestClient(app)
    assert k.get("/api/jembatan/kasus").status_code == 401
    assert k.get("/api/jembatan/kasus", headers={"Authorization": "Bearer salah"}).status_code == 401
    # sesi bendahara pun tidak bisa memakai endpoint jembatan
    assert klien(app, "sri").get("/api/jembatan/kasus").status_code == 401


def test_alur_jembatan_progres_dan_status(env, now):
    app, conn, draf, _ = env
    budi = klien(app, "budi_santoso")
    budi.post("/api/kasus", json=FORM)
    j = TestClient(app)
    baru = j.get("/api/jembatan/kasus", headers=JEMBATAN).json()
    assert [k["id"] for k in baru] == ["kasus-012"]
    assert j.get("/api/jembatan/kasus/kasus-012/berkas/invoice_hotel.txt", headers=JEMBATAN).text == "Hotel 2 malam"
    j.post("/api/jembatan/kasus/kasus-012/diambil", headers=JEMBATAN)
    assert j.get("/api/jembatan/kasus", headers=JEMBATAN).json() == []

    ev = [{"kasus": "kasus-012", "agen": "pembaca-tiket", "aksi": "selesai", "pesan": "1 tiket",
           "waktu": (now + timedelta(seconds=40)).isoformat(), "kunci": "k1"}]
    assert j.post("/api/jembatan/progres", json=ev, headers=JEMBATAN).json() == {"baru": 1}
    assert j.post("/api/jembatan/progres", json=ev, headers=JEMBATAN).json() == {"baru": 0}
    d = budi.get("/api/kasus/kasus-012").json()
    assert d["status"] == "DIPERIKSA_AGEN"
    assert [e["agen"] for e in d["progres"]] == ["jembatan", "pembaca-tiket"]
    assert budi.get(f"/api/kasus/kasus-012?setelah={d['progres'][0]['id']}").json()["progres"][0]["agen"] == "pembaca-tiket"

    # draf disinkronkan, lalu diajukan: status berubah menunggu bendahara
    berkas = {"rekap.xlsx": b"rekap", "kerja/auditor.json": b"{}"}
    import hashlib
    manifest = {k: hashlib.sha256(v).hexdigest() for k, v in berkas.items()}
    perlu = j.post("/api/jembatan/draf/SPJ-2026-012", json=manifest, headers=JEMBATAN).json()["perlu"]
    assert perlu == ["kerja/auditor.json", "rekap.xlsx"]
    for rel in perlu:
        assert j.put(f"/api/jembatan/draf/SPJ-2026-012/{rel}", content=berkas[rel], headers=JEMBATAN).status_code == 200
    assert j.post("/api/jembatan/draf/SPJ-2026-012", json=manifest, headers=JEMBATAN).json()["perlu"] == []
    spj.ajukan(conn, draf, PengajuanSPJ(nomor="SPJ-2026-012", pegawai="Budi Santoso", tujuan="Makassar",
                                        tanggal_spt="2026-10-20 s.d. 2026-10-22", total_diajukan=1, total_dibayar=1),
               "tim_spj", now)
    assert budi.get("/api/kasus/kasus-012").json()["status"] == "MENUNGGU_BENDAHARA"


def test_sinkron_draf_menghapus_berkas_basi_dan_menolak_traversal(env):
    app, _, draf, _ = env
    (draf / "SPJ-2026-012").mkdir(parents=True)
    (draf / "SPJ-2026-012" / "lama.txt").write_text("basi")
    j = TestClient(app)
    j.post("/api/jembatan/draf/SPJ-2026-012", json={}, headers=JEMBATAN)
    assert not (draf / "SPJ-2026-012" / "lama.txt").exists()
    assert j.post("/api/jembatan/draf/SPJ-2026-012", json={"../../x": "a"}, headers=JEMBATAN).status_code == 422
    assert j.post("/api/jembatan/draf/bukan-nomor", json={}, headers=JEMBATAN).status_code == 422
