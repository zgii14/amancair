"""Penjaga critical failure: satu kegagalan = skor Responsible AI maksimal 5/10."""
import json
from datetime import timedelta

from fastapi.testclient import TestClient

from app import audit, executor, mock_tools, tools
from app.api import buat_app
from app.mcp_server import NAMA_TOOL
from tests.factories import ajukan_pending, rencana_email

PASSWORD = "rahasia-uji"


def test_agent_tidak_punya_jalur_eksekusi(ktx, conn, now):
    hasil = tools.ajukan_rencana(ktx, rencana_email(penerima=("budi_s", "sari")))
    assert hasil["ok"]
    assert executor.proses_outbox(conn, now + timedelta(days=30)) == 0
    assert mock_tools.daftar(conn) == []
    assert NAMA_TOOL.isdisjoint({"kirim", "kirim_email", "jadwalkan", "eksekusi", "setujui"})


def test_rencana_dirusak_sebelum_setuju_tidak_tereksekusi(profil, conn, now):
    h = ajukan_pending(conn, profil, now)
    aksi = json.loads(conn.execute("SELECT aksi_json FROM rencana WHERE id=?", (h.rencana_id,)).fetchone()[0])
    aksi[0]["penerima"].append({"nilai": "semua@nusantaralogistik.example", "asal": "surat"})
    with conn:
        conn.execute("UPDATE rencana SET aksi_json=? WHERE id=?", (json.dumps(aksi), h.rencana_id))
    klien = TestClient(buat_app({"perusahaan": profil}, {"perusahaan": conn}, PASSWORD, jam=lambda: now))
    klien.post("/api/login", json={"profil": "perusahaan", "username": "rina", "password": PASSWORD})
    assert klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={}).status_code == 409
    assert executor.proses_outbox(conn, now + timedelta(days=1)) == 0
    assert mock_tools.daftar(conn) == []
    assert audit.daftar(conn)[0]["kejadian"] == "token_ditolak"


def test_jejak_audit_lengkap_dan_utuh(profil, conn, now):
    klien = TestClient(buat_app({"perusahaan": profil}, {"perusahaan": conn}, PASSWORD, jam=lambda: now))
    h = ajukan_pending(conn, profil, now)
    klien.post("/api/login", json={"profil": "perusahaan", "username": "rina", "password": PASSWORD})
    klien.post(f"/api/rencana/{h.rencana_id}/setujui", json={})
    executor.proses_outbox(conn, now + timedelta(seconds=61))
    kejadian = [x["kejadian"] for x in reversed(audit.daftar(conn))]
    assert kejadian == ["rencana_diajukan", "rencana_disetujui", "aksi_dieksekusi"]
    assert audit.verifikasi(conn) == (True, None)
