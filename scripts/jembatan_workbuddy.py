"""Jembatan antara proyek WorkBuddy di laptop dan backend AmanCair (lokal atau online).

Setiap putaran:
1. Mengambil pengajuan baru dari pegawai, menyalin bukti ke data/kasus/<id>/ dan menulis SPT-nya.
2. Melaporkan progres tim agen dari berkas asli: kerja/<agen>_<kasus>.json (waktu tulis berkas)
   dan log/audit.jsonl. Tidak ada progres yang dikarang; yang tidak tertulis di berkas tidak dikirim.
3. Menyamakan folder keluar/draf/SPJ-*/ ke backend supaya ajukan_spj bisa menghitung sidiknya.

Hanya pustaka standar Python. Contoh:
    JEMBATAN_TOKEN=... python scripts/jembatan_workbuddy.py --proyek "D:/Agent 2/spj-agent" --server https://api.contoh.app
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

POLA_KERJA = re.compile(r"^(?P<agen>[a-z-]+)_(?P<kasus>kasus-\d{3}[a-z]?)\.json$")
POLA_KASUS = re.compile(r"^kasus-\d{3}[a-z]?$")
STATE = Path.home() / ".amancair-jembatan.json"


class Klien:
    def __init__(self, server: str, token: str):
        self.server = server.rstrip("/")
        self.token = token

    def _req(self, metode: str, path: str, data: bytes | None = None, tipe: str = "application/json"):
        req = urllib.request.Request(self.server + path, data=data, method=metode,
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": tipe})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def json(self, metode: str, path: str, body=None):
        data = None if body is None else json.dumps(body).encode()
        return json.loads(self._req(metode, path, data) or b"null")

    def unduh(self, path: str) -> bytes:
        return self._req("GET", path)

    def unggah(self, path: str, isi: bytes):
        return self._req("PUT", path, isi, "application/octet-stream")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def waktu_berkas(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat()


def ringkas_kerja(p: Path) -> str:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return "Hasil kerja ditulis"
    if not isinstance(d, dict):
        return "Hasil kerja ditulis"
    # Format alur periksa_aturan: hasil tool di "hasil", temuan auditor di "temuan_final".
    if isinstance(d.get("hasil"), dict):
        d = {**d, **d["hasil"]}
    if isinstance(d.get("temuan_final"), list):
        d = {**d, "temuan": d["temuan_final"]}
    bagian = []
    rp = lambda n: f"Rp{int(n):,}".replace(",", ".")  # noqa: E731
    bukti = d.get("item_bukti")
    if isinstance(bukti, dict):
        bukti = [bukti]
    if isinstance(bukti, list):
        for b in bukti[:4]:
            if isinstance(b, dict):
                teks = f"{b.get('file', b.get('jenis', 'bukti'))}"
                if isinstance(b.get("nominal"), (int, float)):
                    teks += f" {rp(b['nominal'])}"
                if b.get("perintah_tersisip"):
                    teks += " (ada perintah tersisip)"
                bagian.append(teks)
    if isinstance(d.get("verifikasi"), list):
        valid = sum(1 for v in d["verifikasi"] if isinstance(v, dict) and v.get("status") == "VALID")
        bagian.append(f"{valid}/{len(d['verifikasi'])} item valid")
    if isinstance(d.get("total_klaim"), (int, float)):
        bagian.append(f"total klaim {rp(d['total_klaim'])}")
    temuan = d.get("temuan")
    if isinstance(temuan, list):
        level = [t.get("level_risiko") or t.get("level") for t in temuan if isinstance(t, dict)]
        bagian.append(f"{len(temuan)} temuan" + (f" ({', '.join(x for x in level if x)})" if any(level) else ""))
    if isinstance(d.get("total_dibayar"), (int, float)):
        bagian.append(f"diajukan {rp(d.get('total_diajukan', 0))}, dibayar {rp(d['total_dibayar'])}")
    return "; ".join(bagian) or "Hasil kerja ditulis"


def ambil_kasus_baru(k: Klien, proyek: Path) -> None:
    for kasus in k.json("GET", "/api/jembatan/kasus"):
        kid = kasus["id"]
        folder = proyek / "data" / "kasus" / kid
        folder.mkdir(parents=True, exist_ok=True)
        for nama in kasus["berkas"]:
            isi = k.unduh(f"/api/jembatan/kasus/{kid}/berkas/{urllib.parse.quote(nama)}")
            (folder / nama).write_bytes(isi)
        if kasus.get("catatan"):
            (folder / "pesan_pegawai.txt").write_text(kasus["catatan"], encoding="utf-8")
        berangkat, kembali = date.fromisoformat(kasus["tanggal_berangkat"]), date.fromisoformat(kasus["tanggal_kembali"])
        spt = {
            "_watermark": "DATA FIKTIF UNTUK DEMO",
            "_sumber": "Formulir pengajuan pegawai di Meja Pimpinan",
            "nomor_spt": "SPT-2026-" + kid.removeprefix("kasus-"),
            "pegawai": {"nama": kasus["nama_pegawai"]},
            "maksud": kasus["maksud"],
            "tujuan": kasus["tujuan"],
            "tanggal_berangkat": kasus["tanggal_berangkat"],
            "tanggal_kembali": kasus["tanggal_kembali"],
            "lama_hari": (kembali - berangkat).days + 1,
        }
        (proyek / "data" / "spt" / f"{spt['nomor_spt']}.json").write_text(
            json.dumps(spt, ensure_ascii=False, indent=2), encoding="utf-8")
        k.json("POST", f"/api/jembatan/kasus/{kid}/diambil")
        print(f"[kasus] {kid} dari {kasus['nama_pegawai']}: {len(kasus['berkas'])} berkas disalin")


def kirim_progres(k: Klien, proyek: Path, state: dict) -> None:
    kejadian = []
    for p in sorted((proyek / "kerja").glob("*.json")):
        m = POLA_KERJA.match(p.name)
        if not m:
            continue
        kunci = f"kerja:{p.name}:{p.stat().st_mtime_ns}"
        if kunci in state["terkirim"]:
            continue
        kejadian.append({"kasus": m["kasus"], "agen": m["agen"], "aksi": "selesai", "pesan": ringkas_kerja(p),
                         "waktu": waktu_berkas(p), "kunci": kunci})
    log = proyek / "log" / "audit.jsonl"
    if log.is_file():
        for baris in log.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(baris)
            except ValueError:
                continue
            if not POLA_KASUS.match(str(d.get("kasus", ""))) or not d.get("waktu"):
                continue
            kunci = "log:" + hashlib.sha256(baris.encode()).hexdigest()[:32]
            if kunci in state["terkirim"]:
                continue
            kejadian.append({"kasus": d["kasus"], "agen": str(d.get("agen", "?"))[:40],
                             "aksi": str(d.get("aksi", "catat"))[:40], "pesan": str(d.get("keputusan") or "")[:600],
                             "waktu": d["waktu"], "kunci": kunci})
    for i in range(0, len(kejadian), 200):
        potong = kejadian[i:i + 200]
        hasil = k.json("POST", "/api/jembatan/progres", potong)
        state["terkirim"].extend(e["kunci"] for e in potong)
        if hasil["baru"]:
            print(f"[progres] {hasil['baru']} kejadian baru")


def sinkron_draf(k: Klien, proyek: Path, state: dict) -> None:
    for folder in sorted((proyek / "keluar" / "draf").glob("SPJ-*")):
        if not folder.is_dir():
            continue
        manifest = {f.relative_to(folder).as_posix(): sha(f) for f in sorted(folder.rglob("*")) if f.is_file()}
        jejak = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        if state["draf"].get(folder.name) == jejak:
            continue
        perlu = k.json("POST", f"/api/jembatan/draf/{folder.name}", manifest)["perlu"]
        for rel in perlu:
            k.unggah(f"/api/jembatan/draf/{folder.name}/{urllib.parse.quote(rel)}", (folder / rel).read_bytes())
        state["draf"][folder.name] = jejak
        if perlu:
            print(f"[draf] {folder.name}: {len(perlu)} berkas diunggah")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--proyek", required=True, help="Folder proyek WorkBuddy (berisi data/, kerja/, log/, keluar/)")
    ap.add_argument("--server", default="http://127.0.0.1:8000")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--sekali", action="store_true", help="Jalankan satu putaran lalu berhenti")
    args = ap.parse_args()
    token = os.environ.get("JEMBATAN_TOKEN")
    if not token:
        print("JEMBATAN_TOKEN belum diisi", file=sys.stderr)
        return 2
    proyek = Path(args.proyek)
    k = Klien(args.server, token)
    semua = json.loads(STATE.read_text()) if STATE.is_file() else {}
    state = semua.setdefault(k.server, {"terkirim": [], "draf": {}})
    print(f"Jembatan aktif: {proyek} -> {k.server}")
    while True:
        try:
            ambil_kasus_baru(k, proyek)
            kirim_progres(k, proyek, state)
            sinkron_draf(k, proyek, state)
            STATE.write_text(json.dumps(semua))
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[galat] {e}; dicoba lagi", file=sys.stderr)
        if args.sekali:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
