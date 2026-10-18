from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.db import buka
from app.profil import muat_profil

PROFIL_DIR = Path(__file__).resolve().parents[1] / "profil"


@pytest.fixture
def profil():
    return muat_profil(PROFIL_DIR / "perusahaan.yaml")


@pytest.fixture
def conn():
    c = buka(":memory:")
    yield c
    c.close()


@pytest.fixture
def now():
    return datetime(2026, 10, 21, 2, 0, tzinfo=timezone.utc)  # Rabu 09:00 WIB


@pytest.fixture
def ktx(profil, conn, now):
    from app.tools import Konteks
    return Konteks(profil=profil, conn=conn, user_id="rina", jam=lambda: now)
