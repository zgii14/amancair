# Backend Agent Disposisi

## Setup (Windows, Git Bash)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest
```

## Menjalankan API + MCP (satu proses)

```bash
DEMO_PASSWORD=ganti-ini MCP_TOKENS="tok-rina=perusahaan:rina,tok-camat=kecamatan:camat_andi" \
  .venv/Scripts/python -m uvicorn app.api:app_dari_env --factory --port 8000
```

- REST: `http://localhost:8000/api/...` (docs: `/docs`)
- MCP (untuk konektor kustom WorkBuddy): `http://localhost:8000/mcp/` dengan header `Authorization: Bearer tok-rina`
- WorkBuddy di laptop lain / backend remote: buka tunnel, mis. `cloudflared tunnel --url http://localhost:8000`

## MCP via stdio (bila WorkBuddy hanya mendukung stdio)

```bash
MCP_DEFAULT=perusahaan:rina .venv/Scripts/python -m app.mcp_server
```

Mode stdio dan API harus memakai `DATA_DIR` yang sama agar berbagi database.

## Variabel lingkungan

| Nama | Wajib | Keterangan |
|---|---|---|
| `DEMO_PASSWORD` | ya | Password login akun demo Meja Pimpinan |
| `MCP_TOKENS` | tidak | `token=profil:user,...`; tanpa ini MCP HTTP tidak di-mount |
| `FRONTEND_ORIGIN` | tidak | Origin Next.js untuk CORS, dipisah koma |
| `DATA_DIR` | tidak | Folder SQLite (default `data`) |
| `PROFIL_DIR` | tidak | Folder YAML profil (default `profil`) |

Catatan: `mcp` di-pin `<2` karena mcp 2.x mengganti nama `FastMCP` menjadi `MCPServer`.
