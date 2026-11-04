"""Tambah satu baris ke log/audit.jsonl dengan rantai hash.

Jam diisi alat ini dari jam komputer (WITA, ISO 8601), BUKAN dari agen. Kalau agen menyertakan
"waktu", nilainya disimpan sebagai "waktu_klaim_agen" saja, supaya log tidak bisa ditulis
mendahului kejadian.

Pemakaian (panggil SETELAH tindakan benar-benar selesai):
    python tools/audit_helper.py '{"kasus":"kasus-006","agen":"auditor","aksi":"selesai","keputusan":"..."}'
    python tools/audit_helper.py --file entri.json
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone

WITA = timezone(timedelta(hours=8))
AUDIT_PATH = "D:/Agent 2/spj-agent/log/audit.jsonl"


def compute_hash(prev_hash, payload_dict):
    payload = json.dumps(payload_dict, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256((prev_hash + payload).encode('utf-8')).hexdigest()


def append_audit(entry, audit_path=AUDIT_PATH):
    prev_hash = "0" * 64
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                prev_hash = last.get("hash", prev_hash)
    except FileNotFoundError:
        pass

    if "waktu" in entry:
        entry["waktu_klaim_agen"] = entry.pop("waktu")
    entry["waktu"] = datetime.now(WITA).isoformat(timespec="seconds")

    payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    h = compute_hash(prev_hash, payload)
    entry["prev_hash"] = prev_hash
    entry["hash"] = h

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return h


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--file":
        with open(sys.argv[2], encoding="utf-8") as f:
            entri = json.load(f)
    elif len(sys.argv) == 2:
        entri = json.loads(sys.argv[1])
    else:
        print(__doc__)
        sys.exit(1)
    print(append_audit(entri))
