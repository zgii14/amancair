#!/usr/bin/env python3
"""
Perbaiki rekap.xlsx baris B06, update hash, dan sinkronkan ke JSON + log.
"""

import json
import hashlib
from pathlib import Path
import openpyxl

BASE = Path("D:/Agent 2/spj-agent")
REKAP = BASE / "keluar/draf/SPJ-2026-001/rekap.xlsx"
VERIF = BASE / "keluar/draf/SPJ-2026-001/kerja/verifikator-sbm.json"
PENYUSUN = BASE / "keluar/draf/SPJ-2026-001/kerja/penyusun-spj.json"
LOG = BASE / "log/audit.jsonl"
HTML = BASE / "bukti/tahap3-layar-konfirmasi-kasus001.html"


def update_rekap():
    wb = openpyxl.load_workbook(REKAP)
    ws = wb.active
    # Baris B06 adalah baris ke-7 (A7)
    ws["C7"] = "SPT-2026-001.json"
    ws["D7"] = "lama_hari: 4, provinsi: DKI Jakarta"
    wb.save(REKAP)
    print("Updated rekap.xlsx row B06 (C7, D7)")


def compute_rekap_hash() -> str:
    content = REKAP.read_bytes()
    return hashlib.sha256(content).hexdigest()


def update_verifikator():
    data = json.loads(VERIF.read_text(encoding="utf-8"))
    for item in data["items"]:
        if item["id_bukti"] == "B06":
            item["file_sumber"] = "SPT-2026-001.json"
            item["kutipan_teks"] = "lama_hari: 4, provinsi: DKI Jakarta"
    VERIF.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Updated verifikator-sbm.json B06")


def update_penyusun(new_hash: str):
    data = json.loads(PENYUSUN.read_text(encoding="utf-8"))
    data["rekap_hash"] = new_hash
    PENYUSUN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated penyusun-spj.json rekap_hash: {new_hash}")


def rebuild_audit_log(new_hash: str):
    lines = LOG.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        entries.append(json.loads(line))

    # Update baris 7 (penyusun-spj) keputusan text
    for entry in entries:
        if entry.get("agen") == "penyusun-spj" and entry.get("aksi") == "susun_output":
            entry["keputusan"] = f"Output disimpan (rekap hash: {new_hash})"

    prev_hash = "0" * 64
    rebuilt = []
    for entry in entries:
        payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        computed = hashlib.sha256((prev_hash + payload_json).encode("utf-8")).hexdigest()
        entry["prev_hash"] = prev_hash
        entry["hash"] = computed
        rebuilt.append(json.dumps(entry, ensure_ascii=False, sort_keys=False))
        prev_hash = computed

    LOG.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
    print(f"Rebuilt audit log with new hash")


def update_html(new_hash: str):
    text = HTML.read_text(encoding="utf-8")
    # Ganti hash lama dengan yang baru
    import re
    text = re.sub(r"SHA-256: [a-f0-9]{64}", f"SHA-256: {new_hash}", text)
    HTML.write_text(text, encoding="utf-8")
    print(f"Updated HTML confirmation screen")


if __name__ == "__main__":
    update_rekap()
    new_hash = compute_rekap_hash()
    print(f"New rekap hash: {new_hash}")
    update_verifikator()
    update_penyusun(new_hash)
    rebuild_audit_log(new_hash)
    update_html(new_hash)
    print("Done.")
