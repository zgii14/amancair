"""Runner test case Agent Disposisi.

Menjalankan lapis otomatis (pagar pengaman backend) dari testcases/kasus.yaml, menggabungkannya dengan
hasil uji manual agent WorkBuddy (testcases/hasil-manual.yaml), lalu menulis docs/hasil-test.md.

Pakai:  .venv/Scripts/python scripts/jalankan_test.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app import audit, executor, mock_tools, tools
from app.api import buat_app
from app.db import buka
from app.mcp_server import NAMA_TOOL
from app.profil import Profil, muat_profil
from app.rencana import Rencana, ajukan, ambil

ROOT = Path(__file__).resolve().parents[2]
KASUS = ROOT / "testcases" / "kasus.yaml"
MANUAL = ROOT / "testcases" / "hasil-manual.yaml"
LAPORAN = ROOT / "docs" / "hasil-test.md"
NOW = datetime(2026, 10, 19, 1, 0, tzinfo=timezone.utc)  # Senin 09.00 WITA
PASSWORD = "uji-runner"


class Gagal(AssertionError):
    pass


def cek(kondisi: bool, pesan: str) -> None:
    if not kondisi:
        raise Gagal(pesan)


def _profil(pid: str) -> Profil:
    return muat_profil(ROOT / "backend" / "profil" / f"{pid}.yaml")


def _rencana(data: dict, user: str) -> Rencana:
    d = dict(data)
    d.setdefault("pengaju", user)
    d.setdefault("surat", {"input_asli": "(uji otomatis)", "ringkasan": "(uji otomatis)"})
    return Rencana.model_validate(d)


class Lingkungan:
    """Backend lengkap di memori: satu profil, DB baru, jam yang bisa digeser."""

    def __init__(self, pid: str, user_mcp: str):
        self.pid = pid
        self.profil = _profil(pid)
        self.conn = buka(":memory:")
        self.waktu = NOW
        self.app = buat_app({pid: self.profil}, {pid: self.conn}, PASSWORD, jam=lambda: self.waktu,
                            mcp_tokens={"tok-uji": (pid, user_mcp)})

    def klien(self, user: str) -> TestClient:
        k = TestClient(self.app)
        r = k.post("/api/login", json={"profil": self.pid, "username": user, "password": PASSWORD})
        cek(r.status_code == 200, f"login {user} gagal: {r.status_code}")
        return k

    def ajukan(self, rencana: dict, user: str) -> str:
        h = ajukan(self.conn, self.profil, _rencana(rencana, user), self.waktu)
        cek(h.ok, f"rencana uji seharusnya valid: {h.pelanggaran}")
        return h.rencana_id

    def jumlah_terkirim(self) -> int:
        return len(mock_tools.daftar(self.conn))


# ---------------- jenis cek ----------------

def c_ajukan(profil: str, user: str, rencana: dict, harap: dict) -> list[str]:
    p = _profil(profil)
    conn = buka(":memory:")
    h = ajukan(conn, p, _rencana(rencana, user), NOW)
    bukti = []
    kode = {x["kode"] for x in h.pelanggaran}
    if "ok" in harap:
        cek(h.ok == harap["ok"], f"diterima={h.ok}, diharapkan {harap['ok']}; pelanggaran={sorted(kode)}")
        bukti.append("rencana diterima (PENDING)" if h.ok else "rencana ditolak aturan")
    for k in harap.get("kode", []):
        cek(k in kode, f"kode {k} tidak muncul; yang muncul {sorted(kode)}")
        pesan = next(x["pesan"] for x in h.pelanggaran if x["kode"] == k)
        bukti.append(f"{k}: {pesan}")
    if "saran_pertama" in harap:
        cek(h.saran_waktu[:1] == [harap["saran_pertama"]], f"saran {h.saran_waktu[:1]}, diharapkan {harap['saran_pertama']}")
        bukti.append(f"saran slot pertama {h.saran_waktu[0]}")
    for s in harap.get("peringatan_berisi", []):
        cek(any(s in x for x in h.peringatan), f"peringatan '{s}' tidak ada; peringatan={h.peringatan}")
        bukti.append(f"peringatan: …{s}…")
    if "risiko" in harap:
        cek(h.risiko == harap["risiko"], f"risiko {h.risiko}, diharapkan {harap['risiko']}")
        bukti.append(f"risiko {h.risiko}: {'; '.join(h.alasan_risiko)}")
    if "status" in harap:
        st = ambil(conn, h.rencana_id)["status"]
        cek(st == harap["status"], f"status {st}, diharapkan {harap['status']}")
        bukti.append(f"status {st} (menunggu keputusan manusia)")
    return bukti


def c_cari_kontak(profil: str, user: str, kata: str, jumlah: int) -> list[str]:
    ktx = tools.Konteks(profil=_profil(profil), conn=buka(":memory:"), user_id=user, jam=lambda: NOW)
    hasil = tools.cari_kontak(ktx, kata)
    cek(len(hasil) == jumlah, f"{len(hasil)} hasil, diharapkan {jumlah}")
    return [f"cari_kontak('{kata}') → " + ", ".join(f"{h['nama']} ({h['jabatan']})" for h in hasil)]


def c_kalender(profil: str, user: str, kontak: str, dari: str, sampai: str, judul: list[str]) -> list[str]:
    ktx = tools.Konteks(profil=_profil(profil), conn=buka(":memory:"), user_id=user, jam=lambda: NOW)
    hasil = [h["judul"] for h in tools.cek_kalender(ktx, kontak, dari, sampai)]
    cek(hasil == judul, f"judul {hasil}, diharapkan {judul}")
    return [f"cek_kalender sebagai {user} → {hasil}"]


def c_setujui_risiko_tinggi(profil: str, user: str, rencana: dict) -> list[str]:
    env = Lingkungan(profil, user)
    rid = env.ajukan(rencana, user)
    k = env.klien(user)
    r1 = k.post(f"/api/rencana/{rid}/setujui", json={})
    cek(r1.status_code == 428, f"tanpa konfirmasi: {r1.status_code}, diharapkan 428")
    r2 = k.post(f"/api/rencana/{rid}/setujui", json={"konfirmasi_risiko": True})
    cek(r2.status_code == 200, f"dengan konfirmasi: {r2.status_code}, diharapkan 200")
    return ["tanpa centang konfirmasi → 428 " + r1.json()["detail"], "dengan centang → 200, masuk antrean kirim 60 detik"]


def c_setujui(profil: str, pemilik: str, penyetuju: str, rencana: dict, harap_status: int) -> list[str]:
    env = Lingkungan(profil, pemilik)
    rid = env.ajukan(rencana, pemilik)
    r = env.klien(penyetuju).post(f"/api/rencana/{rid}/setujui", json={})
    cek(r.status_code == harap_status, f"status {r.status_code}, diharapkan {harap_status}")
    return [f"{penyetuju} menekan Setujui → {r.status_code} {r.json().get('detail', '')}".strip()]


def c_undo(profil: str, user: str, rencana: dict, detik: int, harap_status: int, harap_terkirim: int) -> list[str]:
    env = Lingkungan(profil, user)
    rid = env.ajukan(rencana, user)
    k = env.klien(user)
    cek(k.post(f"/api/rencana/{rid}/setujui", json={}).status_code == 200, "persetujuan gagal")
    env.waktu = NOW + timedelta(seconds=detik)
    if detik >= 60:
        executor.proses_outbox(env.conn, env.waktu)
    r = k.post(f"/api/rencana/{rid}/undo")
    cek(r.status_code == harap_status, f"undo {r.status_code}, diharapkan {harap_status}")
    executor.proses_outbox(env.conn, NOW + timedelta(seconds=120))
    n = env.jumlah_terkirim()
    cek(n == harap_terkirim, f"terkirim {n}, diharapkan {harap_terkirim}")
    return [f"undo pada detik ke-{detik} → {r.status_code}", f"aksi terkirim: {n}"]


def c_akses_rahasia(profil: str, pemilik: str, tanpa_izin: str, berizin: str, rencana: dict) -> list[str]:
    env = Lingkungan(profil, pemilik)
    rid = env.ajukan(rencana, pemilik)
    staf = env.klien(tanpa_izin)
    cek(all(x["id"] != rid for x in staf.get("/api/rencana").json()), "rencana rahasia muncul di daftar staf")
    ada, tidak_ada = staf.get(f"/api/rencana/{rid}"), staf.get("/api/rencana/tidakpernahada")
    cek(ada.status_code == tidak_ada.status_code == 404, f"status {ada.status_code}/{tidak_ada.status_code}")
    cek(ada.json() == tidak_ada.json(), "respons berbeda: keberadaan rencana bocor")
    cek(env.klien(berizin).get(f"/api/rencana/{rid}").status_code == 200, f"{berizin} tidak bisa melihat")
    return [f"{tanpa_izin}: tidak ada di daftar, detail 404 identik dengan id fiktif", f"{berizin}: dapat melihat (200)"]


def c_tanpa_persetujuan(profil: str, user: str, rencana: dict) -> list[str]:
    p = _profil(profil)
    conn = buka(":memory:")
    ktx = tools.Konteks(profil=p, conn=conn, user_id=user, jam=lambda: NOW)
    h = tools.ajukan_rencana(ktx, _rencana(rencana, user))
    cek(h["ok"], f"pengajuan gagal: {h['pelanggaran']}")
    n = executor.proses_outbox(conn, NOW + timedelta(days=30))
    cek(n == 0 and not mock_tools.daftar(conn), "ada aksi tereksekusi tanpa persetujuan")
    return ["ajukan_rencana via MCP → PENDING", "30 hari kemudian: 0 aksi terkirim", f"tool MCP: {', '.join(sorted(NAMA_TOOL))}"]


def c_rencana_dirusak(profil: str, user: str, rencana: dict, tambah_penerima: str) -> list[str]:
    env = Lingkungan(profil, user)
    rid = env.ajukan(rencana, user)
    aksi = json.loads(env.conn.execute("SELECT aksi_json FROM rencana WHERE id=?", (rid,)).fetchone()[0])
    aksi[0]["penerima"].append({"nilai": tambah_penerima, "asal": "surat"})
    with env.conn:
        env.conn.execute("UPDATE rencana SET aksi_json=? WHERE id=?", (json.dumps(aksi), rid))
    r = env.klien(user).post(f"/api/rencana/{rid}/setujui", json={})
    cek(r.status_code == 409, f"status {r.status_code}, diharapkan 409")
    executor.proses_outbox(env.conn, NOW + timedelta(days=1))
    cek(env.jumlah_terkirim() == 0, "aksi rencana rusak terkirim")
    kejadian = audit.daftar(env.conn)[0]["kejadian"]
    cek(kejadian == "token_ditolak", f"audit terakhir {kejadian}")
    return [f"Setujui → 409 {r.json()['detail']}", "0 aksi terkirim", "audit mencatat token_ditolak"]


def c_audit_dirusak(profil: str, user: str, rencana: dict) -> list[str]:
    env = Lingkungan(profil, user)
    rid = env.ajukan(rencana, user)
    k = env.klien(user)
    k.post(f"/api/rencana/{rid}/setujui", json={})
    cek(k.get("/api/audit/verifikasi").json()["valid"] is True, "rantai awal tidak utuh")
    with env.conn:
        env.conn.execute("UPDATE audit_log SET aktor='orang_lain' WHERE seq=1")
    v = k.get("/api/audit/verifikasi").json()
    cek(v == {"valid": False, "seq_rusak": 1}, f"verifikasi {v}")
    return ["sebelum diubah: rantai utuh", "setelah catatan #1 diedit: rantai rusak di #1"]


def c_mcp_tanpa_token(profil: str, user: str) -> list[str]:
    env = Lingkungan(profil, user)
    k = TestClient(env.app)
    a = k.post("/mcp/", json={}).status_code
    b = k.post("/mcp/", json={}, headers={"Authorization": "Bearer salah"}).status_code
    cek(a == b == 401, f"status {a}/{b}")
    return ["tanpa token → 401", "token salah → 401"]


CEK = {
    "ajukan": c_ajukan,
    "cari_kontak": c_cari_kontak,
    "kalender": c_kalender,
    "setujui_risiko_tinggi": c_setujui_risiko_tinggi,
    "setujui": c_setujui,
    "undo": c_undo,
    "akses_rahasia": c_akses_rahasia,
    "tanpa_persetujuan": c_tanpa_persetujuan,
    "rencana_dirusak": c_rencana_dirusak,
    "audit_dirusak": c_audit_dirusak,
    "mcp_tanpa_token": c_mcp_tanpa_token,
}


# ---------------- runner & laporan ----------------

def muat_kasus() -> list[dict]:
    return yaml.safe_load(KASUS.read_text(encoding="utf-8"))


def jalankan_otomatis(kasus: dict) -> tuple[str, list[str]]:
    oto = kasus.get("otomatis")
    if not oto:
        return "—", []
    params = {k: v for k, v in oto.items() if k != "cek"}
    try:
        return "PASS", CEK[oto["cek"]](**params)
    except Gagal as e:
        return "FAIL", [str(e)]
    except Exception as e:  # noqa: BLE001 — error tak terduga juga harus terlihat di laporan
        return "ERROR", [f"{type(e).__name__}: {e}"]


def _status_agent(k: dict, manual: dict) -> str:
    if not k.get("harapan_agent"):
        return "—"
    return manual.get(k["id"], {}).get("hasil", "BELUM")


def tulis_laporan(kasus: list[dict], hasil: dict[str, tuple[str, list[str]]], manual: dict) -> str:
    oto = [h[0] for h in hasil.values() if h[0] != "—"]
    agent = [_status_agent(k, manual) for k in kasus if k.get("harapan_agent")]
    baris = [
        "# Hasil Test — Agent Disposisi",
        "",
        f"Dibuat otomatis oleh `backend/scripts/jalankan_test.py` · {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        "",
        "Tiap kasus diuji di dua lapis: **sistem** (pagar pengaman backend, otomatis) dan **agent** "
        "(perilaku agent di WorkBuddy, diuji manual dengan screenshot). Kasus yang gagal tetap dilaporkan.",
        "",
        f"- Lapis sistem: **{oto.count('PASS')}/{len(oto)} PASS**"
        + (f" · {len(oto) - oto.count('PASS')} gagal" if oto.count("PASS") != len(oto) else ""),
        f"- Lapis agent: {agent.count('PASS')} PASS · {agent.count('FAIL')} FAIL · {agent.count('BELUM')} belum diuji",
        "",
        "| ID | Skenario | Aturan | Sistem | Agent | Bukti |",
        "|---|---|---|---|---|---|",
    ]
    for k in kasus:
        m = manual.get(k["id"], {})
        bukti = f"[screenshot]({m['bukti']})" if m.get("bukti") else ""
        baris.append(f"| {k['id']} | {k['judul']} | {', '.join(k['aturan'])} | {hasil[k['id']][0]} | "
                     f"{_status_agent(k, manual)} | {bukti} |")
    baris += ["", "## Rincian", ""]
    for k in kasus:
        status, catatan = hasil[k["id"]]
        m = manual.get(k["id"], {})
        baris += [f"### {k['id']} — {k['judul']}", "", f"- Profil: {k['profil']} · Aturan: {', '.join(k['aturan'])}",
                  f"- Input: {k['input']}"]
        if k.get("harapan_agent"):
            baris.append(f"- Harapan agent ({_status_agent(k, manual)}): " + "; ".join(k["harapan_agent"]))
            if m.get("catatan"):
                baris.append(f"  - Catatan penguji: {m['catatan']}")
        if k.get("harapan_sistem"):
            baris.append(f"- Harapan sistem ({status}): " + "; ".join(k["harapan_sistem"]))
            baris += [f"  - {c}" for c in catatan]
        baris.append("")
    return "\n".join(baris)


def main() -> int:
    logging.disable(logging.INFO)  # log request httpx/mcp menutupi ringkasan hasil
    sys.stdout.reconfigure(encoding="utf-8")
    kasus = muat_kasus()
    manual = (yaml.safe_load(MANUAL.read_text(encoding="utf-8")) or {}) if MANUAL.exists() else {}
    hasil = {k["id"]: jalankan_otomatis(k) for k in kasus}
    for k in kasus:
        status, catatan = hasil[k["id"]]
        print(f"{k['id']:5} {status:5} {k['judul']}")
        if status in ("FAIL", "ERROR"):
            print("       " + catatan[0])
    LAPORAN.write_text(tulis_laporan(kasus, hasil, manual), encoding="utf-8")
    print(f"\nLaporan: {LAPORAN.relative_to(ROOT)}")
    return 1 if any(h[0] in ("FAIL", "ERROR") for h in hasil.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
