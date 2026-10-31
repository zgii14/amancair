#!/usr/bin/env python3
"""
Tambahkan entry persetujuan bendahara ke log audit.
"""

import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOG = Path("D:/Agent 2/spj-agent/log/audit.jsonl")

# Waktu sekarang: GMT+7 (WIB) → konversi ke WITA (+08:00)
# current_time = 2026-10-23T11:59:44 GMT+7
# WITA = +08:00, jadi 12:59:44+08:00
now_wita = "2026-10-23T12:59:44+08:00"

# Baca log terakhir untuk prev_hash
lines = LOG.read_text(encoding="utf-8").strip().splitlines()
last_entry = json.loads(lines[-1])
prev_hash = last_entry["hash"]

# Buat entry persetujuan
entry = {
    "waktu": now_wita,
    "kasus": "kasus-001",
    "agen": "bendahara",
    "aksi": "setujui",
    "file_dibaca": "rekap.xlsx",
    "keputusan": "SPJ-2026-001 disetujui. Total dibayar: Rp 8.950.000. File dipindahkan ke keluar/siap-cair/SPJ-2026-001/",
    "aturan": None,
}

# Hitung hash
payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
computed = hashlib.sha256((prev_hash + payload_json).encode("utf-8")).hexdigest()

entry["prev_hash"] = prev_hash
entry["hash"] = computed

# Append ke log
with open(LOG, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False, sort_keys=False) + "\n")

print(f"Entry persetujuan ditambahkan.")
print(f"prev_hash: {prev_hash}")
print(f"hash: {computed}")
