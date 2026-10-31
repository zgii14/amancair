#!/usr/bin/env python3
"""
Eksekusi persetujuan SPJ — salinan byte-per-byte dengan verifikasi SHA-256.

Aturan:
1. Buat manifest.json berisi SHA-256 SEMUA file di folder draf.
2. Salin byte-per-byte (shutil.copy2) dari draf/ ke siap-cair/.
3. Hitung ulang SHA-256 di siap-cair/ dan bandingkan dengan manifest.
4. Bila ada beda → hapus salinan, catat "eksekusi_gagal_versi_berubah" di audit.
5. Persetujuan ditolak (format salah, nomor salah, sidik tidak cocok) dicatat
   di audit dengan aksi "persetujuan_ditolak".
"""

import json
import hashlib
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta


BASE = Path("D:/Agent 2/spj-agent")
LOG = BASE / "log/audit.jsonl"


def sha256_file(path: Path) -> str:
    """Hitung SHA-256 dari isi file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def buat_manifest(draf_dir: Path) -> dict:
    """Buat manifest berisi SHA-256 semua file di folder draf (rekursif)."""
    manifest = {}
    for f in sorted(draf_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(draf_dir).as_posix()
            manifest[rel] = sha256_file(f)
    return manifest


def simpan_manifest(manifest: dict, path: Path):
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def salin_byte_per_byte(draf_dir: Path, siap_dir: Path):
    """Salin semua file dari draf ke siap-cair menggunakan shutil.copy2."""
    if siap_dir.exists():
        shutil.rmtree(siap_dir)
    siap_dir.mkdir(parents=True)
    for src in sorted(draf_dir.rglob("*")):
        if src.is_file():
            rel = src.relative_to(draf_dir)
            dst = siap_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def verifikasi_salinan(siap_dir: Path, manifest: dict) -> list:
    """Verifikasi SHA-256 semua file di siap-cair cocok dengan manifest.
    Kembalikan list file yang tidak cocok."""
    mismatch = []
    for rel, expected_hash in manifest.items():
        f = siap_dir / rel
        if not f.exists():
            mismatch.append((rel, None, expected_hash))
            continue
        actual = sha256_file(f)
        if actual != expected_hash:
            mismatch.append((rel, actual, expected_hash))
    return mismatch


def tambah_audit(aksi: str, keputusan: str, file_dibaca: str = ""):
    """Tambah baris ke log audit."""
    lines = LOG.read_text(encoding="utf-8").strip().splitlines()
    last_entry = json.loads(lines[-1])
    prev_hash = last_entry["hash"]

    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    entry = {
        "waktu": now,
        "kasus": "kasus-001",
        "agen": "koordinator",
        "aksi": aksi,
        "file_dibaca": file_dibaca,
        "keputusan": keputusan,
        "aturan": None,
    }
    payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    computed = hashlib.sha256((prev_hash + payload_json).encode("utf-8")).hexdigest()
    entry["prev_hash"] = prev_hash
    entry["hash"] = computed

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=False) + "\n")
    print(f"Audit: {aksi}")


def eksekusi_persetujuan(spj_nomor: str):
    draf_dir = BASE / f"keluar/draf/{spj_nomor}"
    siap_dir = BASE / f"keluar/siap-cair/{spj_nomor}"

    if not draf_dir.exists():
        print(f"ERROR: Folder draf tidak ditemukan: {draf_dir}")
        tambah_audit(
            "persetujuan_ditolak",
            f"Folder draf {spj_nomor} tidak ditemukan.",
            str(draf_dir),
        )
        return False

    # 1. Buat manifest
    manifest = buat_manifest(draf_dir)
    manifest_path = draf_dir / "manifest.json"
    simpan_manifest(manifest, manifest_path)
    # Update hash manifest.json karena baru ditulis ulang
    manifest["manifest.json"] = sha256_file(manifest_path)
    print(f"Manifest dibuat: {manifest_path}")

    # 2. Salin byte-per-byte
    salin_byte_per_byte(draf_dir, siap_dir)
    print(f"Disalin ke: {siap_dir}")

    # 3. Verifikasi
    mismatch = verifikasi_salinan(siap_dir, manifest)
    if mismatch:
        print("ERROR: File berubah setelah salinan!")
        for rel, actual, expected in mismatch:
            print(f"  {rel}: aktual={actual}, harapan={expected}")
        shutil.rmtree(siap_dir)
        print(f"Salinan dihapus: {siap_dir}")
        tambah_audit(
            "eksekusi_gagal_versi_berubah",
            f"Verifikasi gagal untuk {spj_nomor}. File berbeda: {len(mismatch)}.",
            str(siap_dir),
        )
        return False

    print("Verifikasi lolos: semua file identik.")
    tambah_audit(
        "pencairan",
        f"{spj_nomor} dicairkan. Salinan terverifikasi ({len(manifest)} file).",
        str(siap_dir),
    )
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eksekusi_persetujuan.py SPJ-2026-001")
        sys.exit(1)
    ok = eksekusi_persetujuan(sys.argv[1])
    sys.exit(0 if ok else 1)
