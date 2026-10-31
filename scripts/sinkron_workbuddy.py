"""Salin snapshot proyek WorkBuddy (D:\\Agent 2) ke repo agar ikut dipublikasikan.

Pakai (dari root repo):  python scripts/sinkron_workbuddy.py ["D:/Agent 2"]
Jalankan ulang setiap kali WorkBuddy selesai menghasilkan kasus baru.
"""
import shutil
import sys
from pathlib import Path

SUMBER = Path(sys.argv[1] if len(sys.argv) > 1 else "D:/Agent 2")
REPO = Path(__file__).resolve().parents[1]
TUJUAN = REPO / "workbuddy-spj"
ABAIKAN = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "~$*")


def main() -> None:
    proyek = SUMBER / "spj-agent"
    if not proyek.is_dir():
        sys.exit(f"Folder proyek tidak ditemukan: {proyek}")
    if TUJUAN.exists():
        shutil.rmtree(TUJUAN)
    shutil.copytree(proyek, TUJUAN, ignore=ABAIKAN)
    memori = SUMBER / ".workbuddy-ai" / "memory"
    if memori.is_dir():
        shutil.copytree(memori, TUJUAN / "_bukti-workbuddy" / "memory", ignore=ABAIKAN)
    n = sum(1 for p in TUJUAN.rglob("*") if p.is_file())
    print(f"Disalin {n} berkas ke {TUJUAN.relative_to(REPO)}")


if __name__ == "__main__":
    main()
