import sqlite3
from datetime import datetime, timezone

SKEMA = """
CREATE TABLE IF NOT EXISTS rencana (
  id TEXT PRIMARY KEY,
  pengaju TEXT NOT NULL,
  surat_json TEXT NOT NULL,
  aksi_json TEXT NOT NULL,
  catatan_checker_json TEXT NOT NULL,
  hash TEXT NOT NULL,
  status TEXT NOT NULL,
  risiko TEXT NOT NULL,
  alasan_risiko_json TEXT NOT NULL,
  peringatan_json TEXT NOT NULL,
  dibuat TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approval (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rencana_id TEXT NOT NULL REFERENCES rencana(id),
  rencana_hash TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  disetujui_oleh TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT
);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rencana_id TEXT NOT NULL REFERENCES rencana(id),
  urutan INTEGER NOT NULL,
  aksi_json TEXT NOT NULL,
  send_at TEXT NOT NULL,
  status TEXT NOT NULL,
  undone INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mock_terkirim (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  outbox_id INTEGER NOT NULL REFERENCES outbox(id),
  jenis TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  waktu TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  waktu TEXT NOT NULL,
  aktor TEXT NOT NULL,
  kejadian TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS spj (
  nomor TEXT PRIMARY KEY,
  pengaju TEXT NOT NULL,
  data_json TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  manifest_hash TEXT NOT NULL,
  risiko TEXT NOT NULL,
  status TEXT NOT NULL,
  versi INTEGER NOT NULL DEFAULT 1,
  diajukan TEXT NOT NULL,
  diputuskan_oleh TEXT,
  alasan TEXT
);
CREATE TABLE IF NOT EXISTS kasus (
  id TEXT PRIMARY KEY,
  nomor_spj TEXT NOT NULL,
  pegawai TEXT NOT NULL,
  data_json TEXT NOT NULL,
  berkas_json TEXT NOT NULL,
  status TEXT NOT NULL,
  dibuat TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS progres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kasus TEXT NOT NULL,
  agen TEXT NOT NULL,
  aksi TEXT NOT NULL,
  pesan TEXT NOT NULL,
  waktu TEXT NOT NULL,
  kunci TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS sidik_bukti (
  kunci TEXT NOT NULL,
  nomor_spj TEXT NOT NULL,
  file TEXT,
  sumber TEXT NOT NULL,
  PRIMARY KEY (kunci, nomor_spj)
);
CREATE TABLE IF NOT EXISTS pemeriksaan (
  nomor_spj TEXT PRIMARY KEY,
  hasil_json TEXT NOT NULL,
  waktu TEXT NOT NULL
);
"""


def buka(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SKEMA)
    return conn


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime harus timezone-aware")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
