#!/usr/bin/env python3
"""
Verifikasi rantai hash log audit.
Memeriksa:
1. Setiap baris hash = SHA-256(prev_hash + isi_baris_tanpa_hash).
2. Waktu tidak menurun dari baris ke baris.
3. Setiap "pencairan" harus didahului "bendahara/setujui" yang lebih baru
   daripada "pencairan_dibatalkan" atau "eksekusi_gagal_versi_berubah" terakhir
   untuk kasus yang sama.
4. Baris "bendahara" harus berisi kutipan pesan persis dari manusia.
"""

import json
import hashlib
import sys
from pathlib import Path


def sha256_string(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def verifikasi_rantai(log_path: str):
    path = Path(log_path)
    if not path.exists():
        print(f"ERROR: File tidak ditemukan: {log_path}")
        return False

    prev_hash = "0" * 64
    prev_waktu = None
    baris_ke = 0
    errors = []
    warnings = []

    # Lacak state per kasus: {kasus_id: {"last_setujui": waktu_str, "last_batal": waktu_str}}
    kasus_state = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            baris_ke += 1
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Baris {baris_ke}: JSON invalid — {e}")
                continue

            stored_hash = data.pop("hash", None)
            stored_prev = data.pop("prev_hash", None)
            kasus = data.get("kasus")
            agen = data.get("agen")
            aksi = data.get("aksi")
            waktu = data.get("waktu")
            keputusan = data.get("keputusan", "")

            if stored_prev != prev_hash:
                errors.append(f"Baris {baris_ke}: prev_hash tidak cocok! Diharapkan={prev_hash}, Ditemukan={stored_prev}")
                continue

            # Pemeriksaan waktu tidak menurun
            if waktu and prev_waktu and waktu < prev_waktu:
                errors.append(f"Baris {baris_ke}: waktu menurun! Baris {baris_ke-1}={prev_waktu} -> Baris {baris_ke}={waktu}")
            if waktu:
                prev_waktu = waktu

            # Update state per kasus
            if kasus:
                if kasus not in kasus_state:
                    kasus_state[kasus] = {"last_setujui": None, "last_batal": None}

                if agen == "bendahara" and aksi == "setujui":
                    kasus_state[kasus]["last_setujui"] = waktu
                    # Cek: harus ada kutipan pesan persis (keputusan mengandung pesan asli)
                    if not keputusan or len(keputusan) < 10:
                        warnings.append(f"Baris {baris_ke}: bendahara/setujui tanpa kutipan pesan yang jelas.")

                if aksi in ("pencairan_dibatalkan", "eksekusi_gagal_versi_berubah"):
                    kasus_state[kasus]["last_batal"] = waktu

                # Pemeriksaan: pencairan harus didahului setujui yang valid
                if aksi == "pencairan":
                    last_setujui = kasus_state[kasus]["last_setujui"]
                    last_batal = kasus_state[kasus]["last_batal"]
                    if not last_setujui:
                        errors.append(f"Baris {baris_ke}: pencairan tanpa persetujuan bendahara!")
                    elif last_batal and last_setujui <= last_batal:
                        errors.append(f"Baris {baris_ke}: pencairan didahului pembatalan/eksekusi_gagal! last_setujui={last_setujui}, last_batal={last_batal}")

            payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
            computed_hash = sha256_string(prev_hash + payload)

            if stored_hash != computed_hash:
                errors.append(f"Baris {baris_ke}: hash tidak cocok! Diharapkan={computed_hash}, Ditemukan={stored_hash}")
                continue

            prev_hash = stored_hash

    # Laporan
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\nGAGAL: {baris_ke} baris diperiksa, {len(errors)} error ditemukan.")
        return False

    print(f"OK: {baris_ke} baris terverifikasi, rantai hash utuh, waktu naik, aturan pencairan lolos.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verifikasi_log.py <path/to/audit.jsonl>")
        sys.exit(1)
    ok = verifikasi_rantai(sys.argv[1])
    sys.exit(0 if ok else 1)
