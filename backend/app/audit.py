import hashlib
import json
import sqlite3
from datetime import datetime

from app.db import iso

GENESIS = "0" * 64


def _hitung(prev: str, waktu: str, aktor: str, kejadian: str, payload_json: str) -> str:
    return hashlib.sha256(f"{prev}|{waktu}|{aktor}|{kejadian}|{payload_json}".encode("utf-8")).hexdigest()


def catat(conn: sqlite3.Connection, aktor: str, kejadian: str, payload: dict, waktu: datetime) -> str:
    w = iso(waktu)
    row = conn.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else GENESIS
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    h = _hitung(prev, w, aktor, kejadian, payload_json)
    conn.execute(
        "INSERT INTO audit_log (waktu, aktor, kejadian, payload_json, prev_hash, hash) VALUES (?,?,?,?,?,?)",
        (w, aktor, kejadian, payload_json, prev, h),
    )
    return h


def verifikasi(conn: sqlite3.Connection) -> tuple[bool, int | None]:
    prev = GENESIS
    for r in conn.execute("SELECT * FROM audit_log ORDER BY seq"):
        if r["prev_hash"] != prev or _hitung(prev, r["waktu"], r["aktor"], r["kejadian"], r["payload_json"]) != r["hash"]:
            return False, r["seq"]
        prev = r["hash"]
    return True, None


def daftar(conn: sqlite3.Connection, batas: int = 200) -> list[dict]:
    rows = conn.execute("SELECT * FROM audit_log ORDER BY seq DESC LIMIT ?", (batas,)).fetchall()
    return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]
