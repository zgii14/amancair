from datetime import datetime, timedelta, timezone

from app.rules import cek_disposisi, cek_waktu_rapat, saran_slot

WIB = timezone(timedelta(hours=7))
WITA = timezone(timedelta(hours=8))


def kode(ps):
    return {p.kode for p in ps}


def test_jumat_siang_bentrok_jumatan(profil):
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 23, 12, 0, tzinfo=WIB), 60, ["WIB"])
    assert "JUMATAN" in kode(ps)


def test_jumat_setelah_jumatan_lolos(profil):
    assert cek_waktu_rapat(profil, datetime(2026, 10, 23, 13, 0, tzinfo=WIB), 60, ["WIB"]) == []


def test_jumatan_dicek_per_zona_peserta(profil):
    # 13.00 WITA = 12.00 WIB -> peserta WIB masih salat Jumat
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 23, 13, 0, tzinfo=WITA), 60, ["WIB", "WITA"])
    jumatan = [p for p in ps if p.kode == "JUMATAN"]
    assert len(jumatan) == 1
    assert "WIB" in jumatan[0].pesan


def test_diluar_jam_kerja(profil):
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 21, 15, 30, tzinfo=WIB), 60, ["WIB"])
    assert "DILUAR_JAM_KERJA" in kode(ps)


def test_jam_kerja_peserta_wit(profil):
    # 15.00 WIB = 17.00 WIT
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 21, 15, 0, tzinfo=WIB), 60, ["WIB", "WIT"])
    assert [p.kode for p in ps] == ["DILUAR_JAM_KERJA"]
    assert "WIT" in ps[0].pesan


def test_akhir_pekan(profil):
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 24, 10, 0, tzinfo=WIB), 60, ["WIB"])
    assert "AKHIR_PEKAN" in kode(ps)


def test_libur(profil):
    ps = cek_waktu_rapat(profil, datetime(2026, 12, 25, 9, 0, tzinfo=WIB), 60, ["WIB"])
    assert "LIBUR" in kode(ps)


def test_waktu_tanpa_zona(profil):
    ps = cek_waktu_rapat(profil, datetime(2026, 10, 21, 10, 0), 60, ["WIB"])
    assert kode(ps) == {"WAKTU_TANPA_ZONA"}


def test_saran_slot_setelah_jumatan(profil):
    s = saran_slot(profil, datetime(2026, 10, 23, 12, 0, tzinfo=WIB), 60, ["WIB"])
    assert s[0] == datetime(2026, 10, 23, 13, 0, tzinfo=WIB)
    assert len(s) == 3
    assert all(cek_waktu_rapat(profil, x, 60, ["WIB"]) == [] for x in s)


def test_disposisi_ke_bawah_lolos(profil):
    assert cek_disposisi(profil, "rina", "budi_s", "Hadiri dan laporkan") == []


def test_disposisi_instruksi_tidak_peka_huruf(profil):
    assert cek_disposisi(profil, "rina", "sari", "hadiri dan laporkan") == []


def test_disposisi_ke_atas_ditolak(profil):
    assert "HIERARKI" in kode(cek_disposisi(profil, "budi_s", "rina", "Untuk diketahui"))


def test_disposisi_sejajar_ditolak(profil):
    assert "HIERARKI" in kode(cek_disposisi(profil, "budi_s", "budi_h", "Untuk diketahui"))


def test_instruksi_tidak_baku(profil):
    assert kode(cek_disposisi(profil, "rina", "sari", "Kerjakan secepatnya")) == {"INSTRUKSI_TIDAK_BAKU"}


def test_disposisi_kontak_tidak_dikenal(profil):
    assert "HIERARKI" in kode(cek_disposisi(profil, "rina", "hantu", "Setuju"))
