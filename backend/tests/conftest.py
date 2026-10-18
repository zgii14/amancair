from pathlib import Path

import pytest

from app.profil import muat_profil

PROFIL_DIR = Path(__file__).resolve().parents[1] / "profil"


@pytest.fixture
def profil():
    return muat_profil(PROFIL_DIR / "perusahaan.yaml")
