import json
from datetime import timedelta

import pytest

from app import approval
from app.approval import TokenError
from tests.factories import ajukan_pending


def terbit(conn, h, now):
    with conn:
        return approval.terbitkan(conn, h.rencana_id, h.hash, "rina", now)


def test_token_valid_sekali_pakai(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    t = terbit(conn, h, now)
    with conn:
        row = approval.pakai(conn, t, now)
    assert row["rencana_id"] == h.rencana_id
    with pytest.raises(TokenError, match="sudah dipakai"):
        approval.pakai(conn, t, now)


def test_token_kedaluwarsa(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    t = terbit(conn, h, now)
    with pytest.raises(TokenError, match="kedaluwarsa"):
        approval.pakai(conn, t, now + timedelta(minutes=6))


def test_token_palsu(conn):
    with pytest.raises(TokenError, match="tidak dikenal"):
        approval.pakai(conn, "ngarang", None)


def test_rencana_diubah_setelah_approval(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    t = terbit(conn, h, now)
    r = conn.execute("SELECT aksi_json FROM rencana WHERE id=?", (h.rencana_id,)).fetchone()
    aksi = json.loads(r["aksi_json"])
    aksi[0]["penerima"].append({"nilai": "yosef", "asal": "surat"})
    with conn:
        conn.execute("UPDATE rencana SET aksi_json=? WHERE id=?", (json.dumps(aksi), h.rencana_id))
    with pytest.raises(TokenError, match="berubah"):
        approval.pakai(conn, t, now)


def test_token_disimpan_sebagai_hash(conn, profil, now):
    h = ajukan_pending(conn, profil, now)
    t = terbit(conn, h, now)
    row = conn.execute("SELECT * FROM approval").fetchone()
    assert t not in tuple(str(v) for v in tuple(row))
