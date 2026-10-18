from app.rencana import Aksi, Asal, Nilai, Rencana, SuratTerstruktur, ajukan


def nilai(v, asal=Asal.PIMPINAN):
    return Nilai(nilai=v, asal=asal)


def surat(**kw):
    base = {"input_asli": "Tolong kirim notulen ke Pak Budi ya.", "ringkasan": "Kirim notulen ke Pak Budi."}
    base.update(kw)
    return SuratTerstruktur(**base)


def rencana_email(penerima=("budi_s",), asal=Asal.PIMPINAN, pengaju="rina", **surat_kw):
    return Rencana(
        pengaju=pengaju,
        surat=surat(**surat_kw),
        aksi=[Aksi(
            jenis="email",
            penerima=[nilai(p, asal) for p in penerima],
            judul="Notulen rapat",
            isi=nilai("Terlampir notulen rapat.", Asal.SURAT),
        )],
    )


def rencana_jadwal(waktu, penerima=("budi_s",), pengaju="rina"):
    return Rencana(
        pengaju=pengaju,
        surat=surat(),
        aksi=[Aksi(
            jenis="jadwal",
            penerima=[nilai(p) for p in penerima],
            judul="Follow-up notulen",
            isi=nilai("Follow-up hasil rapat."),
            waktu_mulai=nilai(waktu),
        )],
    )


def rencana_disposisi(penerima="budi_s", instruksi="Hadiri dan laporkan", pengaju="rina"):
    return Rencana(
        pengaju=pengaju,
        surat=surat(input_asli="Undangan rapat koordinasi.", ringkasan="Undangan rapat koordinasi."),
        aksi=[Aksi(
            jenis="disposisi",
            penerima=[nilai(penerima)],
            judul="Disposisi undangan",
            isi=nilai("Mohon dihadiri.", Asal.PIMPINAN),
            instruksi=instruksi,
            tenggat="2026-10-22",
        )],
    )


def ajukan_pending(conn, profil, now, r=None):
    hasil = ajukan(conn, profil, r or rencana_email(), now)
    assert hasil.ok, hasil.pelanggaran
    return hasil
