from __future__ import annotations

import asyncio
import os
import secrets
import shutil
import sqlite3
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import approval, audit, executor, kasus, mock_tools, spj
from app import rencana as rencana_mod
from app.db import buka, iso
from app.mcp_server import app_http, buat_server, parse_tokens
from app.profil import Profil, muat_profil


class LoginBody(BaseModel):
    profil: str
    username: str
    password: str


class SetujuiBody(BaseModel):
    konfirmasi_risiko: bool = False


class TolakBody(BaseModel):
    alasan: str


TIDAK_DITEMUKAN = "Rencana tidak ditemukan"


def buat_app(
    profil: dict[str, Profil],
    conns: dict[str, sqlite3.Connection],
    password: str,
    jam: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    mcp_tokens: dict[str, tuple[str, str]] | None = None,
    origins: list[str] = (),
    interval_outbox: float = 5.0,
    spj_dirs: dict[str, tuple[Path, Path]] | None = None,
    mcp_hosts: list[str] | None = None,
    kasus_root: Path | None = None,
    jembatan: tuple[str, str] | None = None,
) -> FastAPI:
    sesi: dict[str, dict] = {}
    spj_dirs = spj_dirs or {}
    mcp = buat_server(profil, conns, jam, mcp_tokens, spj_dirs=spj_dirs, allowed_hosts=mcp_hosts) if mcp_tokens else None
    mcp_asgi = app_http(mcp, mcp_tokens) if mcp else None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async def loop_outbox():
            while True:
                for c in conns.values():
                    executor.proses_outbox(c, jam())
                await asyncio.sleep(interval_outbox)

        async with AsyncExitStack() as stack:
            if mcp is not None:
                await stack.enter_async_context(mcp.session_manager.run())
            task = asyncio.create_task(loop_outbox())
            try:
                yield
            finally:
                task.cancel()

    app = FastAPI(title="Agent Disposisi API", lifespan=lifespan)
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_credentials=True,
                           allow_methods=["*"], allow_headers=["*"])
    if mcp_asgi is not None:
        app.mount("/mcp", mcp_asgi)

    def user_aktif(sid: str | None = Cookie(default=None)) -> dict:
        if not sid or sid not in sesi:
            raise HTTPException(401, "Belum login")
        return sesi[sid]

    def konteks(u: dict):
        p = profil[u["profil"]]
        return p, conns[u["profil"]], p.jabatan_kontak(u["username"])

    def ambil_terlihat(c, j, rid: str) -> dict:
        r = rencana_mod.ambil(c, rid)
        if r is None or r["surat"]["sifat"] not in j.sifat_boleh:
            raise HTTPException(404, TIDAK_DITEMUKAN)
        return r

    @app.post("/api/login")
    async def login(body: LoginBody, response: Response):
        p = profil.get(body.profil)
        k = p.kontak_by_id(body.username) if p else None
        if k is None or not secrets.compare_digest(body.password, password):
            raise HTTPException(401, "Login gagal")
        sid = secrets.token_urlsafe(32)
        sesi[sid] = {"profil": body.profil, "username": body.username}
        response.set_cookie("sid", sid, httponly=True, samesite="lax")
        j = p.jabatan_by_id(k.jabatan)
        return {"nama": k.nama, "jabatan": j.nama, "boleh_menyetujui": j.boleh_menyetujui, "profil": body.profil}

    @app.post("/api/logout")
    async def logout(response: Response, sid: str | None = Cookie(default=None)):
        sesi.pop(sid or "", None)
        response.delete_cookie("sid")
        return {"ok": True}

    @app.get("/api/me")
    async def me(u: dict = Depends(user_aktif)):
        p, _, j = konteks(u)
        k = p.kontak_by_id(u["username"])
        return {"nama": k.nama, "jabatan": j.nama, "boleh_menyetujui": j.boleh_menyetujui, "profil": u["profil"]}

    @app.get("/api/profil")
    async def profil_aktif(u: dict = Depends(user_aktif)):
        p, _, _ = konteks(u)
        return {
            "nama_org": p.nama_org,
            "instruksi_disposisi": p.instruksi_disposisi,
            "kontak": [
                {"id": k.id, "nama": k.nama, "jabatan": p.jabatan_by_id(k.jabatan).nama, "email": k.email, "zona": k.zona}
                for k in p.kontak
            ],
        }

    @app.get("/api/rencana")
    async def daftar_rencana(status: str | None = None, u: dict = Depends(user_aktif)):
        _, c, j = konteks(u)
        return [r for r in rencana_mod.daftar(c, status) if r["surat"]["sifat"] in j.sifat_boleh]

    @app.get("/api/rencana/{rid}")
    async def detail_rencana(rid: str, u: dict = Depends(user_aktif)):
        _, c, j = konteks(u)
        return ambil_terlihat(c, j, rid)

    @app.post("/api/rencana/{rid}/setujui")
    async def setujui(rid: str, body: SetujuiBody, u: dict = Depends(user_aktif)):
        _, c, j = konteks(u)
        r = ambil_terlihat(c, j, rid)
        if not j.boleh_menyetujui:
            raise HTTPException(403, "Jabatan Anda tidak berwenang menyetujui")
        if r["status"] != "PENDING":
            raise HTTPException(409, f"Rencana berstatus {r['status']}")
        if r["risiko"] == "tinggi" and not body.konfirmasi_risiko:
            raise HTTPException(428, "Rencana berisiko tinggi: perlu konfirmasi tambahan")
        now = jam()
        with c:
            token = approval.terbitkan(c, rid, r["hash"], u["username"], now)
        try:
            ids = executor.jalankan(c, token, now)
        except approval.TokenError as e:
            raise HTTPException(409, str(e))
        return {"outbox_ids": ids, "bisa_undo_sampai": iso(now + executor.JEDA_UNDO)}

    @app.post("/api/rencana/{rid}/tolak")
    async def tolak(rid: str, body: TolakBody, u: dict = Depends(user_aktif)):
        _, c, j = konteks(u)
        r = ambil_terlihat(c, j, rid)
        if not j.boleh_menyetujui:
            raise HTTPException(403, "Jabatan Anda tidak berwenang menolak")
        if r["status"] != "PENDING":
            raise HTTPException(409, f"Rencana berstatus {r['status']}")
        with c:
            rencana_mod.ubah_status(c, rid, "DITOLAK")
            audit.catat(c, u["username"], "rencana_ditolak", {"rencana_id": rid, "alasan": body.alasan}, jam())
        return {"ok": True}

    @app.post("/api/rencana/{rid}/undo")
    async def undo(rid: str, u: dict = Depends(user_aktif)):
        _, c, j = konteks(u)
        ambil_terlihat(c, j, rid)
        try:
            n = executor.undo(c, rid, u["username"], jam())
        except executor.UndoError as e:
            raise HTTPException(409, str(e))
        return {"dibatalkan": n}

    # ---------------- SPJ: gerbang persetujuan bendahara ----------------

    def spj_konteks(u: dict):
        p, c, j = konteks(u)
        dirs = spj_dirs.get(u["profil"])
        if dirs is None or not (j.boleh_menyetujui or "rahasia" in j.sifat_boleh):
            raise HTTPException(404, "SPJ tidak ditemukan")
        return c, j, dirs

    @app.get("/api/spj")
    async def daftar_spj(status: str | None = None, u: dict = Depends(user_aktif)):
        if u["profil"] not in spj_dirs:
            return []
        c, _, _ = spj_konteks(u)
        return spj.daftar(c, status)

    @app.get("/api/spj/{nomor}")
    async def detail_spj(nomor: str, u: dict = Depends(user_aktif)):
        c, _, _ = spj_konteks(u)
        r = spj.ambil(c, nomor)
        if r is None:
            raise HTTPException(404, "SPJ tidak ditemukan")
        return r

    @app.get("/api/spj/{nomor}/berkas/{relatif:path}")
    async def berkas_spj(nomor: str, relatif: str, u: dict = Depends(user_aktif)):
        c, _, (draf, _siap) = spj_konteks(u)
        r = spj.ambil(c, nomor)
        if r is None or relatif not in r["manifest"]:
            raise HTTPException(404, "Berkas tidak ditemukan")
        try:
            return FileResponse(spj.path_berkas(draf, nomor, relatif))
        except spj.SPJError:
            raise HTTPException(404, "Berkas tidak ditemukan")

    @app.post("/api/spj/{nomor}/setujui")
    async def setujui_spj(nomor: str, body: SetujuiBody, u: dict = Depends(user_aktif)):
        c, j, (draf, siap) = spj_konteks(u)
        if not j.boleh_menyetujui:
            raise HTTPException(403, "Jabatan Anda tidak berwenang menyetujui SPJ")
        try:
            return spj.setujui(c, draf, siap, nomor, u["username"], body.konfirmasi_risiko, jam())
        except spj.SPJError as e:
            raise HTTPException(428 if "konfirmasi" in str(e) else 409, str(e))

    @app.post("/api/spj/{nomor}/tolak")
    async def tolak_spj(nomor: str, body: TolakBody, u: dict = Depends(user_aktif)):
        c, j, _ = spj_konteks(u)
        if not j.boleh_menyetujui:
            raise HTTPException(403, "Jabatan Anda tidak berwenang menolak SPJ")
        try:
            return spj.tolak(c, nomor, u["username"], body.alasan, jam())
        except spj.SPJError as e:
            raise HTTPException(409, str(e))

    # ---------------- Kasus: pegawai mengajukan, tim agen memproses ----------------

    def kasus_konteks(u: dict):
        p, c, j = konteks(u)
        if u["profil"] not in spj_dirs or kasus_root is None:
            raise HTTPException(404, "Fitur pengajuan SPJ tidak aktif")
        pemeriksa = j.boleh_menyetujui or "rahasia" in j.sifat_boleh
        return p, c, pemeriksa

    def ringkas(c, kid: str, row: dict | None) -> dict:
        nomor = row["nomor_spj"] if row else kasus.nomor_spj(kid)
        s = spj.ambil(c, nomor)
        if s is None and not row:
            s = spj.ambil(c, nomor + "b")
        semua = kasus.progres(c, kid)
        jumlah = len(semua)
        if s is not None:
            status = {"PENDING": "MENUNGGU_BENDAHARA"}.get(s["status"], s["status"])
        elif jumlah or (row and row["status_kasus"] == "DIAMBIL_AGEN"):
            status = "DIPERIKSA_AGEN"
        else:
            status = "DITERIMA"
        dasar = row or {"id": kid, "nomor_spj": s["nomor"] if s else nomor, "pegawai": None,
                        "nama_pegawai": s["pegawai"] if s else None, "tujuan": s["tujuan"] if s else None,
                        "berkas": [], "dibuat": s["diajukan"] if s else None}
        spj_ringkas = None if s is None else {
            "nomor": s["nomor"], "status": s["status"], "risiko": s["risiko"], "total_diajukan": s["total_diajukan"],
            "total_dibayar": s["total_dibayar"], "alasan": s["alasan"], "jumlah_temuan": len(s["temuan"])}
        return {**dasar, "status": status, "spj": spj_ringkas, "jumlah_progres": jumlah,
                "aktivitas_terakhir": max((e["waktu"] for e in semua), default=None)}

    def kasus_terlihat(c, p, u, pemeriksa: bool, kid: str) -> dict:
        row = kasus.ambil(c, kid)
        hasil = ringkas(c, kid, row)
        if pemeriksa and (row or hasil["jumlah_progres"] or hasil["spj"]):
            return hasil
        nama = p.kontak_by_id(u["username"]).nama
        if (row and row["pegawai"] == u["username"]) or (not row and hasil["spj"] and hasil["nama_pegawai"] == nama):
            return hasil
        raise HTTPException(404, "Pengajuan tidak ditemukan")

    @app.post("/api/kasus")
    async def ajukan_kasus(body: kasus.PengajuanKasus, u: dict = Depends(user_aktif)):
        p, c, _ = kasus_konteks(u)
        try:
            row = kasus.ajukan(c, kasus_root, u["username"], p.kontak_by_id(u["username"]).nama, body, jam())
        except kasus.KasusError as e:
            raise HTTPException(422, str(e))
        return ringkas(c, row["id"], row)

    @app.get("/api/kasus")
    async def daftar_kasus(u: dict = Depends(user_aktif)):
        p, c, pemeriksa = kasus_konteks(u)
        if pemeriksa:
            rows = {r["id"]: r for r in kasus.daftar(c)}
            ids = set(rows) | set(kasus.kasus_dengan_progres(c))
        else:
            rows = {r["id"]: r for r in kasus.daftar(c, u["username"])}
            nama = p.kontak_by_id(u["username"]).nama
            ids = set(rows) | {"kasus-" + s["nomor"][9:12] for s in spj.daftar(c) if s["pegawai"] == nama}
        return sorted((ringkas(c, kid, rows.get(kid)) for kid in ids), key=lambda r: r["id"], reverse=True)

    @app.get("/api/kasus/{kid}")
    async def detail_kasus(kid: str, setelah: int = 0, u: dict = Depends(user_aktif)):
        p, c, pemeriksa = kasus_konteks(u)
        hasil = kasus_terlihat(c, p, u, pemeriksa, kid)
        return {**hasil, "progres": kasus.progres(c, kid, setelah)}

    @app.get("/api/kasus/{kid}/berkas/{nama}")
    async def berkas_kasus(kid: str, nama: str, u: dict = Depends(user_aktif)):
        p, c, pemeriksa = kasus_konteks(u)
        kasus_terlihat(c, p, u, pemeriksa, kid)
        try:
            return FileResponse(kasus.path_berkas(kasus_root, kid, nama))
        except kasus.KasusError:
            raise HTTPException(404, "Berkas tidak ditemukan")

    # ---------------- Jembatan: skrip di laptop WorkBuddy ----------------

    def jembatan_konteks(authorization: str | None = Header(default=None)):
        if jembatan is None or kasus_root is None:
            raise HTTPException(404, "Jembatan tidak aktif")
        token, pid = jembatan
        if not authorization or not secrets.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "Token jembatan salah")
        return conns[pid], spj_dirs[pid][0]

    @app.get("/api/jembatan/kasus")
    async def jembatan_kasus_baru(k=Depends(jembatan_konteks)):
        return [r for r in kasus.daftar(k[0]) if r["status_kasus"] == "DITERIMA"]

    @app.get("/api/jembatan/kasus/{kid}/berkas/{nama}")
    async def jembatan_berkas(kid: str, nama: str, k=Depends(jembatan_konteks)):
        try:
            return FileResponse(kasus.path_berkas(kasus_root, kid, nama))
        except kasus.KasusError:
            raise HTTPException(404, "Berkas tidak ditemukan")

    @app.post("/api/jembatan/kasus/{kid}/diambil")
    async def jembatan_diambil(kid: str, k=Depends(jembatan_konteks)):
        kasus.tandai_diambil(k[0], kid, jam())
        return {"ok": True}

    @app.post("/api/jembatan/progres")
    async def jembatan_progres(body: list[kasus.Kejadian], k=Depends(jembatan_konteks)):
        return {"baru": kasus.catat_progres(k[0], body)}

    @app.post("/api/jembatan/draf/{nomor}")
    async def jembatan_sinkron_draf(nomor: str, body: dict[str, str], k=Depends(jembatan_konteks)):
        try:
            return {"perlu": spj.sinkron_draf(k[1], nomor, body)}
        except spj.SPJError as e:
            raise HTTPException(422, str(e))

    @app.put("/api/jembatan/draf/{nomor}/{relatif:path}")
    async def jembatan_tulis_draf(nomor: str, relatif: str, request: Request, k=Depends(jembatan_konteks)):
        try:
            spj.tulis_draf(k[1], nomor, relatif, await request.body())
        except spj.SPJError as e:
            raise HTTPException(422, str(e))
        return {"ok": True}

    @app.get("/api/terkirim")
    async def terkirim(u: dict = Depends(user_aktif)):
        _, c, _ = konteks(u)
        return mock_tools.daftar(c)

    @app.get("/api/audit")
    async def daftar_audit(u: dict = Depends(user_aktif)):
        _, c, _ = konteks(u)
        return audit.daftar(c)

    @app.get("/api/audit/verifikasi")
    async def verifikasi_audit(u: dict = Depends(user_aktif)):
        _, c, _ = konteks(u)
        valid, seq = audit.verifikasi(c)
        return {"valid": valid, "seq_rusak": seq}

    return app


def app_dari_env() -> FastAPI:
    profil_dir = Path(os.environ.get("PROFIL_DIR", Path(__file__).resolve().parents[1] / "profil"))
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    data_dir.mkdir(exist_ok=True)
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_PASSWORD wajib diisi")
    profil = {p.stem: muat_profil(p) for p in profil_dir.glob("*.yaml")}
    conns = {pid: buka(str(data_dir / f"{pid}.db")) for pid in profil}
    tokens = parse_tokens(os.environ.get("MCP_TOKENS", ""))
    for pid, uid in tokens.values():
        if pid not in profil or profil[pid].kontak_by_id(uid) is None:
            raise RuntimeError(f"MCP_TOKENS merujuk user tidak dikenal: {pid}:{uid}")
    origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "").split(",") if o.strip()]
    spj_dirs = {}
    if os.environ.get("SPJ_DRAF_ROOT"):
        # siap-cair sengaja di luar folder kerja agen: hanya backend yang bisa menulisnya.
        siap = Path(os.environ.get("SPJ_SIAP_ROOT", data_dir / "siap-cair"))
        spj_dirs[os.environ.get("SPJ_PROFIL", "diskominfo")] = (Path(os.environ["SPJ_DRAF_ROOT"]), siap)
    if os.environ.get("SPJ_DRAF_CONTOH"):
        # Draf contoh di image disalin sekali ke folder draf (di volume) supaya bisa ditimpa jembatan.
        for draf, _siap in spj_dirs.values():
            for sumber in Path(os.environ["SPJ_DRAF_CONTOH"]).iterdir():
                if sumber.is_dir() and not (draf / sumber.name).exists():
                    shutil.copytree(sumber, draf / sumber.name)
    if os.environ.get("SPJ_SEED_FILE"):
        for pid, (draf, _siap) in spj_dirs.items():
            spj.seed(conns[pid], draf, Path(os.environ["SPJ_SEED_FILE"]), datetime.now(timezone.utc))
    # Railway mengisi RAILWAY_PUBLIC_DOMAIN otomatis; MCP_ALLOWED_HOSTS untuk domain lain.
    hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        hosts.append(os.environ["RAILWAY_PUBLIC_DOMAIN"])
    kasus_root = data_dir / "kasus" if spj_dirs else None
    token_jembatan = os.environ.get("JEMBATAN_TOKEN")
    jembatan = (token_jembatan, next(iter(spj_dirs))) if token_jembatan and spj_dirs else None
    return buat_app(profil, conns, password, mcp_tokens=tokens or None, origins=origins, spj_dirs=spj_dirs,
                    mcp_hosts=hosts, kasus_root=kasus_root, jembatan=jembatan)
