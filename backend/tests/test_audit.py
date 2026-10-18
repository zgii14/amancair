from datetime import datetime

import pytest

from app import audit


def isi_dua(conn, now):
    with conn:
        audit.catat(conn, "agent", "a", {"x": 1}, now)
        audit.catat(conn, "rina", "b", {"y": 2}, now)


def test_rantai_valid(conn, now):
    isi_dua(conn, now)
    assert audit.verifikasi(conn) == (True, None)


def test_rantai_kosong_valid(conn):
    assert audit.verifikasi(conn) == (True, None)


def test_edit_diam_diam_ketahuan(conn, now):
    isi_dua(conn, now)
    with conn:
        conn.execute("UPDATE audit_log SET payload_json=? WHERE seq=1", ('{"x": 999}',))
    assert audit.verifikasi(conn) == (False, 1)


def test_hapus_baris_ketahuan(conn, now):
    isi_dua(conn, now)
    with conn:
        conn.execute("DELETE FROM audit_log WHERE seq=1")
    assert audit.verifikasi(conn) == (False, 2)


def test_daftar_terbaru_dulu(conn, now):
    isi_dua(conn, now)
    d = audit.daftar(conn)
    assert [x["kejadian"] for x in d] == ["b", "a"]
    assert d[0]["payload"] == {"y": 2}


def test_waktu_naive_ditolak(conn):
    with pytest.raises(ValueError):
        audit.catat(conn, "agent", "a", {}, datetime(2026, 10, 21, 9, 0))
