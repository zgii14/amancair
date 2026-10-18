import asyncio

from starlette.testclient import TestClient

from app.mcp_server import NAMA_TOOL, app_http, buat_server, identitas_dari_header, parse_tokens

TOKENS = {"tok-rina": ("perusahaan", "rina")}


def test_parse_tokens():
    assert parse_tokens("a=perusahaan:rina, b=kecamatan:camat_andi") == {
        "a": ("perusahaan", "rina"),
        "b": ("kecamatan", "camat_andi"),
    }
    assert parse_tokens("") == {}


def test_identitas_dari_header():
    assert identitas_dari_header("Bearer tok-rina", TOKENS, None) == ("perusahaan", "rina")
    assert identitas_dari_header("Bearer salah", TOKENS, ("perusahaan", "rina")) is None
    assert identitas_dari_header(None, TOKENS, ("perusahaan", "rina")) == ("perusahaan", "rina")
    assert identitas_dari_header(None, TOKENS, None) is None


def test_hanya_tool_baca_dan_ajukan(profil, conn, now):
    mcp = buat_server({"perusahaan": profil}, {"perusahaan": conn}, lambda: now, TOKENS)
    nama = {t.name for t in asyncio.run(mcp.list_tools())}
    assert nama == NAMA_TOOL == {"cari_kontak", "cek_kalender", "cek_aturan", "profil_org", "ajukan_rencana"}


def test_http_tanpa_token_401(profil, conn, now):
    mcp = buat_server({"perusahaan": profil}, {"perusahaan": conn}, lambda: now, TOKENS)
    klien = TestClient(app_http(mcp, TOKENS))
    assert klien.post("/", json={}).status_code == 401
    assert klien.post("/", json={}, headers={"Authorization": "Bearer salah"}).status_code == 401
