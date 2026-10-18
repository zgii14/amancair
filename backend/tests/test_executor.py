from datetime import timedelta

import pytest

from app import approval, audit, executor, mock_tools
from app.approval import TokenError
from app.executor import UndoError
from app.rencana import ambil
from tests.factories import ajukan_pending


def setujui(conn, h, now):
    with conn:
        t = approval.terbitkan(conn, h.rencana_id, h.hash, "rina", now)
    return executor.jalankan(conn, t, now)


def jumlah(conn, tabel):
    return conn.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]


def test_tanpa_token_valid_tidak_ada_eksekusi(conn, profil, now):
    ajukan_pending(conn, profil, now)
    with pytest.raises(TokenError):
        executor.jalankan(conn, "palsu", now)
    assert jumlah(conn, "outbox") == 0
    assert executor.proses_outbox(conn, now + timedelta(days=1)) == 0
    assert mock_tools.daftar(conn) == []
    assert audit.daftar(conn)[0]["kejadian"] == "token_ditolak"


def test_setuju_ditahan_60_detik_lalu_terkirim(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    ids = setujui(conn, h, now)
    assert len(ids) == 1
    assert ambil(conn, h.rencana_id)["status"] == "DISETUJUI"
    assert executor.proses_outbox(conn, now + timedelta(seconds=30)) == 0
    assert executor.proses_outbox(conn, now + timedelta(seconds=61)) == 1
    terkirim = mock_tools.daftar(conn)
    assert len(terkirim) == 1 and terkirim[0]["jenis"] == "email"
    assert ambil(conn, h.rencana_id)["status"] == "DIEKSEKUSI"


def test_undo_dalam_60_detik(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    setujui(conn, h, now)
    assert executor.undo(conn, h.rencana_id, "rina", now + timedelta(seconds=30)) == 1
    assert executor.proses_outbox(conn, now + timedelta(seconds=61)) == 0
    assert mock_tools.daftar(conn) == []
    assert ambil(conn, h.rencana_id)["status"] == "DIBATALKAN"


def test_undo_setelah_jendela_lewat(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    setujui(conn, h, now)
    with pytest.raises(UndoError):
        executor.undo(conn, h.rencana_id, "rina", now + timedelta(seconds=61))


def test_token_tidak_bisa_dipakai_ulang(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    with conn:
        t = approval.terbitkan(conn, h.rencana_id, h.hash, "rina", now)
    executor.jalankan(conn, t, now)
    with pytest.raises(TokenError):
        executor.jalankan(conn, t, now)
    assert jumlah(conn, "outbox") == 1


def test_rencana_bukan_pending_ditolak(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    with conn:
        conn.execute("UPDATE rencana SET status='DITOLAK' WHERE id=?", (h.rencana_id,))
        t = approval.terbitkan(conn, h.rencana_id, h.hash, "rina", now)
    with pytest.raises(TokenError, match="bukan PENDING"):
        executor.jalankan(conn, t, now)
    assert jumlah(conn, "outbox") == 0


def test_audit_tetap_valid_setelah_alur_penuh(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    setujui(conn, h, now)
    executor.proses_outbox(conn, now + timedelta(seconds=61))
    kejadian = [x["kejadian"] for x in reversed(audit.daftar(conn))]
    assert kejadian == ["rencana_diajukan", "rencana_disetujui", "aksi_dieksekusi"]
    assert audit.verifikasi(conn) == (True, None)
