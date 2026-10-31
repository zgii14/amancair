#!/usr/bin/env python3
"""
Tools perhitungan SPJ — hitung_malam, hitung_hari_spt, rekap_total.
Semua hitungan menggunakan skrip ini agar bisa diulang dan diaudit.
"""

from datetime import datetime, date
from typing import List, Dict
import json


def hitung_malam(check_in_str: str, check_out_str: str) -> int:
    """Hitung jumlah malam hotel dari check-in ke check-out."""
    fmt = "%Y-%m-%d"
    d1 = datetime.strptime(check_in_str, fmt).date()
    d2 = datetime.strptime(check_out_str, fmt).date()
    selisih = (d2 - d1).days
    return max(selisih, 0)


def hitung_hari_spt(berangkat_str: str, kembali_str: str) -> int:
    """Hitung lama hari SPT (termasuk hari berangkat dan kembali)."""
    fmt = "%Y-%m-%d"
    d1 = datetime.strptime(berangkat_str, fmt).date()
    d2 = datetime.strptime(kembali_str, fmt).date()
    selisih = (d2 - d1).days + 1
    return max(selisih, 0)


def biaya_per_malam_incl_pajak(total_invoice: int, jumlah_malam: int) -> float:
    """Biaya hotel per malam termasuk pajak & service = total invoice / jumlah malam."""
    if jumlah_malam <= 0:
        return 0.0
    return total_invoice / jumlah_malam


def rekap_total(items: List[Dict]) -> Dict:
    """
    Rekap total dari daftar item bukti.
    Input: list dict dengan key 'nilai_diajukan' dan 'nilai_dibayar'
    Output: dict total_diajukan, total_dibayar, selisih
    """
    total_diajukan = sum(item.get("nilai_diajukan", 0) for item in items)
    total_dibayar = sum(
        item.get("nilai_dibayar", item.get("nilai_diajukan", 0))
        for item in items
        if item.get("status") != "ditolak"
    )
    return {
        "total_diajukan": total_diajukan,
        "total_dibayar": total_dibayar,
        "selisih": total_diajukan - total_dibayar,
    }


def cek_tanggal_di_dalam_spt(tanggal_str: str, berangkat_str: str, kembali_str: str, boleh_h1: bool = False) -> bool:
    """Cek apakah tanggal berada di dalam masa SPT."""
    fmt = "%Y-%m-%d"
    t = datetime.strptime(tanggal_str, fmt).date()
    b = datetime.strptime(berangkat_str, fmt).date()
    k = datetime.strptime(kembali_str, fmt).date()

    if boleh_h1:
        b = b - __import__("datetime").timedelta(days=1)

    return b <= t <= k


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python hitung.py <command> [args...]")
        print("Commands: malam <check_in> <check_out> | hari <berangkat> <kembali> | malam_pajak <total> <malam>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "malam":
        print(hitung_malam(sys.argv[2], sys.argv[3]))
    elif cmd == "hari":
        print(hitung_hari_spt(sys.argv[2], sys.argv[3]))
    elif cmd == "malam_pajak":
        print(biaya_per_malam_incl_pajak(int(sys.argv[2]), int(sys.argv[3])))
    else:
        print("Unknown command")
