import json
import sqlite3
from datetime import datetime, timedelta

from app import approval, audit, mock_tools
from app import rencana as rencana_mod
from app.approval import TokenError
from app.db import iso

JEDA_UNDO = timedelta(seconds=60)


class UndoError(Exception):
    pass


def jalankan(conn: sqlite3.Connection, token: str, now: datetime) -> list[int]:
    try:
        with conn:
            appr = approval.pakai(conn, token, now)
            r = rencana_mod.ambil(conn, appr["rencana_id"])
            if r["status"] != "PENDING":
                raise TokenError(f"rencana berstatus {r['status']}, bukan PENDING")
            send_at = iso(now + JEDA_UNDO)
            ids: list[int] = []
            for urutan, aksi in enumerate(r["aksi"]):
                cur = conn.execute(
                    "INSERT INTO outbox (rencana_id, urutan, aksi_json, send_at, status) VALUES (?,?,?,?,?)",
                    (r["id"], urutan, json.dumps(aksi, ensure_ascii=False), send_at, "MENUNGGU"),
                )
                ids.append(cur.lastrowid)
            rencana_mod.ubah_status(conn, r["id"], "DISETUJUI")
            audit.catat(conn, appr["disetujui_oleh"], "rencana_disetujui",
                        {"rencana_id": r["id"], "hash": r["hash"], "kirim_pada": send_at}, now)
        return ids
    except TokenError as e:
        with conn:
            audit.catat(conn, "executor", "token_ditolak", {"alasan": str(e)}, now)
        raise


def proses_outbox(conn: sqlite3.Connection, now: datetime) -> int:
    rows = conn.execute(
        "SELECT * FROM outbox WHERE status='MENUNGGU' AND send_at<=? ORDER BY id", (iso(now),)
    ).fetchall()
    for row in rows:
        aksi = json.loads(row["aksi_json"])
        with conn:
            mock_tools.kirim(conn, row["id"], aksi, now)
            conn.execute("UPDATE outbox SET status='TERKIRIM' WHERE id=?", (row["id"],))
            audit.catat(conn, "executor", "aksi_dieksekusi",
                        {"rencana_id": row["rencana_id"], "outbox_id": row["id"], "jenis": aksi["jenis"]}, now)
            sisa = conn.execute(
                "SELECT COUNT(*) FROM outbox WHERE rencana_id=? AND status='MENUNGGU'", (row["rencana_id"],)
            ).fetchone()[0]
            if sisa == 0:
                rencana_mod.ubah_status(conn, row["rencana_id"], "DIEKSEKUSI")
    return len(rows)


def undo(conn: sqlite3.Connection, rencana_id: str, oleh: str, now: datetime) -> int:
    with conn:
        cur = conn.execute(
            "UPDATE outbox SET status='DIBATALKAN', undone=1 WHERE rencana_id=? AND status='MENUNGGU' AND send_at>?",
            (rencana_id, iso(now)),
        )
        if cur.rowcount == 0:
            raise UndoError("Jendela undo sudah lewat atau tidak ada aksi yang menunggu.")
        rencana_mod.ubah_status(conn, rencana_id, "DIBATALKAN")
        audit.catat(conn, oleh, "rencana_dibatalkan", {"rencana_id": rencana_id, "jumlah_aksi": cur.rowcount}, now)
    return cur.rowcount
