import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

from app import rencana as rencana_mod
from app.db import iso

TTL = timedelta(minutes=5)


class TokenError(Exception):
    pass


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def terbitkan(conn: sqlite3.Connection, rencana_id: str, rencana_hash: str, oleh: str, now: datetime) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO approval (rencana_id, rencana_hash, token_hash, disetujui_oleh, expires_at) VALUES (?,?,?,?,?)",
        (rencana_id, rencana_hash, _h(token), oleh, iso(now + TTL)),
    )
    return token


def pakai(conn: sqlite3.Connection, token: str, now: datetime) -> dict:
    row = conn.execute("SELECT * FROM approval WHERE token_hash=?", (_h(token),)).fetchone()
    if row is None:
        raise TokenError("token tidak dikenal")
    if row["used_at"]:
        raise TokenError("token sudah dipakai")
    if iso(now) > row["expires_at"]:
        raise TokenError("token kedaluwarsa")
    r = rencana_mod.ambil(conn, row["rencana_id"])
    if r is None:
        raise TokenError("rencana tidak ditemukan")
    dihitung = rencana_mod.hash_rencana(rencana_mod.rencana_dari_baris(r))
    if r["hash"] != row["rencana_hash"] or dihitung != row["rencana_hash"]:
        raise TokenError("rencana berubah setelah disetujui")
    conn.execute("UPDATE approval SET used_at=? WHERE id=?", (iso(now), row["id"]))
    return dict(row)
