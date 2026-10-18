"""Tiruan email/kalender/task/registri disposisi. Hanya dipanggil oleh executor."""
import json
import sqlite3
from datetime import datetime

from app.db import iso


def kirim(conn: sqlite3.Connection, outbox_id: int, aksi: dict, now: datetime) -> int:
    cur = conn.execute(
        "INSERT INTO mock_terkirim (outbox_id, jenis, payload_json, waktu) VALUES (?,?,?,?)",
        (outbox_id, aksi["jenis"], json.dumps(aksi, ensure_ascii=False), iso(now)),
    )
    return cur.lastrowid


def daftar(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM mock_terkirim ORDER BY id DESC").fetchall()
    return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]
