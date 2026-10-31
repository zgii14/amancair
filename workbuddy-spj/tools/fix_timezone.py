#!/usr/bin/env python3
"""
Script untuk memperbaiki timezone dan rebuild hash chain untuk kasus-001.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
import shutil

BASE = Path("D:/Agent 2/spj-agent")
KERJA = BASE / "keluar/draf/SPJ-2026-001/kerja"
LOG = BASE / "log/audit.jsonl"

# Mapping perubahan waktu di kerja/*.json dan log/audit.jsonl
# Format: (old_str, new_str)
TIME_FIXES = [
    # koordinator: WIB → WITA (+1 jam)
    ("2026-10-23T11:14:15.262156+08:00", "2026-10-23T12:14:15.262156+08:00"),
    # pembaca-hotel: UTC → WITA (+8 jam)
    ("2026-10-23T04:15:30+08:00", "2026-10-23T12:15:30+08:00"),
    # pembaca-tiket: UTC → WITA
    ("2026-10-23T04:15:36.894038+08:00", "2026-10-23T12:15:36.894038+08:00"),
    # pembaca-struk: UTC → WITA
    ("2026-10-23T04:15:42+08:00", "2026-10-23T12:15:42+08:00"),
    # verifikator-sbm: UTC → WITA
    ("2026-10-23T04:18:02+08:00", "2026-10-23T12:18:02+08:00"),
    # auditor: UTC → WITA
    ("2026-10-23T04:20:00+08:00", "2026-10-23T12:20:00+08:00"),
    # penyusun-spj: WIB → WITA (+1 jam)
    ("2026-10-23T12:32:01.722137+08:00", "2026-10-23T13:32:01.722137+08:00"),
]


def fix_json_file(path: Path):
    """Ganti string waktu lama dengan yang baru di file JSON."""
    text = path.read_text(encoding="utf-8")
    for old, new in TIME_FIXES:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"Fixed: {path}")


def fix_kerja_files():
    """Perbaiki semua file kerja/*.json."""
    for f in KERJA.glob("*.json"):
        fix_json_file(f)


def rebuild_audit_log():
    """Baca audit.jsonl, perbaiki waktu, rebuild hash chain."""
    lines = LOG.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        text = line
        for old, new in TIME_FIXES:
            text = text.replace(old, new)
        entries.append(json.loads(text))

    prev_hash = "0" * 64
    rebuilt = []
    for entry in entries:
        # buat payload tanpa hash & prev_hash
        payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        computed = hashlib.sha256((prev_hash + payload_json).encode("utf-8")).hexdigest()
        entry["prev_hash"] = prev_hash
        entry["hash"] = computed
        rebuilt.append(json.dumps(entry, ensure_ascii=False, sort_keys=False))
        prev_hash = computed

    LOG.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
    print(f"Rebuilt: {LOG}")
    return True


if __name__ == "__main__":
    fix_kerja_files()
    rebuild_audit_log()
    print("Done.")
