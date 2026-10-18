from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import executor
from app.api import buat_app
from tests.factories import ajukan_pending, rencana_email

PASSWORD = "rahasia-uji"


@pytest.fixture
def waktu(now):
    return {"now": now}


@pytest.fixture
def klien(profil, conn, waktu):
    app = buat_app({"perusahaan": profil}, {"perusahaan": conn}, PASSWORD, jam=lambda: waktu["now"],
                   mcp_tokens={"tok-rina": ("perusahaan", "rina")})
    return TestClient(app)


def login(klien, username="rina"):
    r = klien.post("/api/login", json={"profil": "perusahaan", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()


def test_tanpa_login_401(klien):
    assert klien.get("/api/rencana").status_code == 401


def test_password_salah_401(klien):
    r = klien.post("/api/login", json={"profil": "perusahaan", "username": "rina", "password": "salah"})
    assert r.status_code == 401


def test_me(klien):
    login(klien)
    assert klien.get("/api/me").json()["boleh_menyetujui"] is True


def test_profil_untuk_ui(klien):
    login(klien)
    p = klien.get("/api/profil").json()
    assert "Hadiri dan laporkan" in p["instruksi_disposisi"]
    assert {"id": "budi_h", "nama": "Budi Hartono", "jabatan": "Manajer Operasional",
            "email": "budi.hartono@nusantaralogistik.example", "zona": "WITA"} in p["kontak"]


def test_setujui_lalu_terkirim_setelah_jeda(klien, conn, profil, now, waktu):
    h = ajukan_pending(conn, profil, now)
    login(klien)
    r = klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={})
    assert r.status_code == 200, r.text
    assert len(r.json()["outbox_ids"]) == 1
    assert executor.proses_outbox(conn, now + timedelta(seconds=61)) == 1
    assert len(klien.get("/api/terkirim").json()) == 1
    assert klien.get(f"/api/rencana/{h.rencana_id}").json()["status"] == "DIEKSEKUSI"


def test_staf_tidak_bisa_menyetujui(klien, conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    login(klien, "sari")
    assert klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={}).status_code == 403


def test_risiko_tinggi_butuh_konfirmasi(klien, conn, profil, now):
    h = ajukan_pending(conn, profil, now, rencana_email(penerima=("vendor@contoh.example",)))
    login(klien)
    assert klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={}).status_code == 428
    assert klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={"konfirmasi_risiko": True}).status_code == 200


def test_surat_rahasia_tidak_bocor_ke_staf(klien, conn, profil, now):
    h = ajukan_pending(conn, profil, now, rencana_email(sifat="rahasia"))
    login(klien, "sari")
    assert klien.get("/api/rencana").json() == []
    ada = klien.get(f"/api/rencana/{h.rencana_id}")
    tidak_ada = klien.get("/api/rencana/idngarang123")
    assert ada.status_code == tidak_ada.status_code == 404
    assert ada.json() == tidak_ada.json()


def test_undo_via_api(klien, conn, profil, now, waktu):
    h = ajukan_pending(conn, profil, now)
    login(klien)
    klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={})
    waktu["now"] = now + timedelta(seconds=30)
    assert klien.post(f"/api/rencana/{h.rencana_id}/undo").status_code == 200
    waktu["now"] = now + timedelta(seconds=90)
    assert klien.post(f"/api/rencana/{h.rencana_id}/undo").status_code == 409


def test_tolak_lalu_tidak_bisa_disetujui(klien, conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    login(klien)
    assert klien.post(f"/api/rencana/{h.rencana_id}/tolak", json={"alasan": "Salah Budi"}).status_code == 200
    assert klien.get(f"/api/rencana/{h.rencana_id}").json()["status"] == "DITOLAK"
    assert klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={}).status_code == 409


def test_audit_dan_verifikasi(klien, conn, profil, now):
    ajukan_pending(conn, profil, now)
    login(klien)
    assert klien.get("/api/audit").json()[0]["kejadian"] == "rencana_diajukan"
    assert klien.get("/api/audit/verifikasi").json() == {"valid": True, "seq_rusak": None}


def test_mcp_tanpa_token_401(klien):
    assert klien.post("/mcp/", json={}).status_code == 401
