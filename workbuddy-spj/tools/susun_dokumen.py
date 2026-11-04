#!/usr/bin/env python3
"""Susun dokumen draf SPJ dari hasil kerja tim, dengan templat tetap.

Membaca:
  kerja/verifikator-sbm_<kasus>.json   (hasil periksa_aturan di kunci "hasil")
  kerja/auditor_<kasus>.json           (temuan_final, timeline; boleh belum ada)
  data/spt/<SPT>.json, data/master/satker.json

Menulis ke keluar/draf/<nomor SPJ>/:
  rekap.xlsx, draf_spj.docx, layar_konfirmasi.html, timeline.json

Mencetak JSON ringkasan untuk dipakai apa adanya saat memanggil ajukan_spj.

Pemakaian:
    python tools/susun_dokumen.py kasus-011
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

BASE = Path(__file__).resolve().parents[1]
FONT = "Times New Roman"
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]

JENIS = {"tiket": "Tiket pesawat", "boarding_pass": "Boarding pass", "hotel": "Hotel", "taksi": "Taksi",
         "makan": "Makan", "lain": "Lainnya"}
STATUS = {"SESUAI": "Layak", "DIPOTONG": "Sebagian", "DITOLAK": "Tidak dibayar", "DITAHAN": "Ditahan",
          "GANDA": "Tidak dibayar", "PERLU_CEK_MANUSIA": "Perlu dicek petugas",
          "TERMASUK_UANG_HARIAN": "Tidak dibayar"}
TINGKAT = {"KRITIS": "Sangat penting", "TINGGI": "Penting", "SEDANG": "Perlu dicek", "RENDAH": "Informasi"}
URUT = {"KRITIS": 0, "TINGGI": 1, "SEDANG": 2, "RENDAH": 3}
TINDAK = {"KRITIS": "Tahan pembayaran bagian ini sampai ada penjelasan.",
          "TINGGI": "Bendahara memberi persetujuan khusus sebelum dibayar.",
          "SEDANG": "Minta penjelasan atau bukti tambahan dari pegawai.",
          "RENDAH": "Tidak perlu tindakan."}
HAL = {"R01": "Di luar masa tugas", "R02": "Nama pada bukti", "R03": "Hotel melebihi batas biaya",
       "R04": "Uang harian", "R05": "Taksi melebihi batas biaya", "R06": "Bukti ganda",
       "R07": "Hari libur nasional", "R08": "Nominal tidak terbaca", "R09": "Tulisan perintah di dalam bukti",
       "R10": "Perlu persetujuan khusus", "R11": "Biaya makan", "KELENGKAPAN": "Bukti belum lengkap",
       "AUDITOR": "Catatan pemeriksa"}


def rp(n: int | float) -> str:
    return "Rp" + f"{int(round(n)):,}".replace(",", ".")


def tgl(s: str | None) -> str:
    if not s:
        return "-"
    d = date.fromisoformat(s[:10])
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def rentang(a: str, b: str) -> str:
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    if da == db:
        return tgl(a)
    if (da.year, da.month) == (db.year, db.month):
        return f"{da.day}–{db.day} {BULAN[db.month - 1]} {db.year}"
    return f"{tgl(a)} – {tgl(b)}"


SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]


def terbilang(n: int) -> str:
    n = int(n)
    if n < 12:
        return SATUAN[n]
    if n < 20:
        return terbilang(n - 10) + " belas"
    if n < 100:
        return (terbilang(n // 10) + " puluh " + terbilang(n % 10)).strip()
    if n < 200:
        return ("seratus " + terbilang(n - 100)).strip()
    if n < 1000:
        return (terbilang(n // 100) + " ratus " + terbilang(n % 100)).strip()
    if n < 2000:
        return ("seribu " + terbilang(n - 1000)).strip()
    for batas, nama in ((10**12, "triliun"), (10**9, "miliar"), (10**6, "juta"), (10**3, "ribu")):
        if n >= batas:
            return (terbilang(n // batas) + f" {nama} " + terbilang(n % batas)).strip()
    return ""


def rupiah_terbilang(n: int) -> str:
    teks = terbilang(n) if n else "nol"
    return (teks[0].upper() + teks[1:] + " rupiah").replace("  ", " ")


BERKAS = re.compile(r"\b[\w-]+\.(?:txt|pdf|jpe?g|png)\b", re.IGNORECASE)


def kapital(teks: str) -> str:
    return teks[:1].upper() + teks[1:]


def bersih(teks: str) -> str:
    """Buang kode aturan dan istilah teknis; nama berkas dipindah ke akhir kalimat sebagai rujukan bukti."""
    teks = re.sub(r"\s*\((?:R\d{2}[^)]*|KELENGKAPAN)\)", "", teks)
    teks = teks.replace("Wajib konfirmasi tambahan bendahara:", "Perlu persetujuan khusus bendahara karena")
    teks = teks.replace("ada item ditolak atau ditahan", "ada bagian yang ditolak atau ditahan")
    teks = teks.replace("periksa_aturan", "pemeriksaan aturan").replace("pengelola SPJ lewat NIP", "pengelola SPJ melalui NIP")
    berkas = list(dict.fromkeys(BERKAS.findall(teks)))
    if berkas:
        # "1 malam di invoice_hotel.txt di luar ..." -> "1 malam di luar ...": kata depan ikut dibuang bersama nama berkas.
        teks = re.sub(r"\s*\b(?:di|pada|dalam)\s+(?=" + BERKAS.pattern[2:-2] + r")", " ", teks, flags=re.IGNORECASE)
        teks = BERKAS.sub("", teks)
        teks = re.sub(r"\s{2,}", " ", teks).replace(" ;", ";").replace(" ,", ",").replace("( ", "(").strip(" ;,")
        teks = teks.rstrip(".") + f" (bukti: {', '.join(berkas)})."
    return kapital(teks.strip())


def penjelasan(t: dict) -> str:
    """Kalimat temuan dalam bahasa sehari-hari."""
    d = t.get("deskripsi", "")
    if t["aturan"] == "R09":
        kutipan = re.search(r'"([^"]+)"', d)
        bukti = BERKAS.search(d)
        return (f"Di dalam bukti{' ' + bukti[0] if bukti else ''} terdapat tulisan yang berisi perintah"
                f"{': “' + kutipan[1] + '”' if kutipan else ''}. Tulisan ini tidak diikuti dan tidak "
                f"memengaruhi perhitungan.")
    if t["aturan"] == "R11":
        nilai = re.search(r"Rp[\d.]+", d)
        bukti = BERKAS.search(d)
        return (f"Biaya makan{' ' + nilai[0] if nilai else ''} tidak dibayar karena sudah termasuk uang harian"
                f"{' (bukti: ' + bukti[0] + ')' if bukti else ''}.")
    if t["aturan"] == "R06" and "sudah pernah diajukan" in d:
        nomor = re.search(r"nomor ([^)]+)\)", d)
        spj = re.search(r"SPJ-\d{4}-\d{3}[a-z]?", d)
        bukti = BERKAS.search(d)
        return (f"Struk{' nomor ' + nomor[1] if nomor else ''} sudah pernah diajukan pada "
                f"{spj[0] if spj else 'SPJ lain'}, sehingga tidak dapat dibayar lagi"
                f"{' (bukti: ' + bukti[0] + ')' if bukti else ''}.")
    return bersih(d)


def keterangan(it: dict, sbm: dict) -> str:
    s, rumus = it["status"], it.get("rumus", "")
    if it["jenis"] == "hotel" and s in ("SESUAI", "DIPOTONG"):
        m = re.match(r"(\d+) dari (\d+) malam", rumus)
        malam_sah, malam = (int(m[1]), int(m[2])) if m else (None, None)
        per_malam = it["nilai_diajukan"] / malam if malam else 0
        bagian = []
        if malam_sah is not None and malam_sah < malam:
            bagian.append(f"dibayar {malam_sah} dari {malam} malam (sisanya di luar masa tugas)")
        else:
            bagian.append(f"{malam} malam")
        if per_malam > sbm["pagu_hotel"]:
            bagian.append(f"{rp(per_malam)}/malam melebihi batas {rp(sbm['pagu_hotel'])}, dibayar sebatas batas")
        else:
            bagian.append(f"{rp(per_malam)}/malam, dalam batas {rp(sbm['pagu_hotel'])}")
        return kapital("; ".join(bagian))
    if it["jenis"] == "taksi" and s == "DIPOTONG":
        return f"Melebihi batas taksi, dibayar {rp(sbm['pagu_taksi'])}"
    if s == "SESUAI":
        return "Sesuai bukti"
    if s == "TERMASUK_UANG_HARIAN":
        return "Biaya makan sudah termasuk uang harian"
    if s == "GANDA":
        return "Sama dengan bukti lain, hanya dihitung sekali"
    if s == "PERLU_CEK_MANUSIA":
        return "Nominal tidak terbaca, perlu dicek petugas"
    if s == "DITOLAK":
        return "Tanggal di luar masa tugas"
    if s == "DITAHAN":
        if "Sudah diajukan di" in rumus:
            return "Bukti sudah dipakai di " + re.search(r"SPJ-\d{4}-\d{3}[a-z]?", rumus)[0] + ", ditahan"
        return "Nama pada bukti berbeda, ditahan sampai ada penjelasan"
    return bersih(rumus)


def uraian(it: dict) -> str:
    j = JENIS.get(it["jenis"], it["jenis"])
    if it["jenis"] == "hotel":
        return f"{j}, {rentang(it['check_in'], it['check_out'])}"
    return f"{j}, {tgl(it.get('tanggal'))}"


def muat(kasus: str) -> dict:
    kerja = BASE / "kerja"
    v = json.loads((kerja / f"verifikator-sbm_{kasus}.json").read_text(encoding="utf-8"))
    hasil = v["hasil"] if "hasil" in v else v
    auditor_f = kerja / f"auditor_{kasus}.json"
    a = json.loads(auditor_f.read_text(encoding="utf-8")) if auditor_f.is_file() else {}
    nomor = hasil["nomor_spj"]
    spt_f = BASE / "data" / "spt" / ("SPT-" + nomor[4:] + ".json")
    spt = json.loads(spt_f.read_text(encoding="utf-8"))
    satker = json.loads((BASE / "data" / "master" / "satker.json").read_text(encoding="utf-8"))
    temuan = a.get("temuan_final") or hasil["temuan"]
    temuan = sorted(temuan, key=lambda t: URUT.get(t["level"], 9))
    return {"kasus": kasus, "nomor": nomor, "hasil": hasil, "spt": spt, "satker": satker, "temuan": temuan,
            "timeline": a.get("timeline", [])}


def baris_biaya(d: dict) -> list[dict]:
    h = d["hasil"]
    rows = [{"uraian": uraian(it), "bukti": it["file"], "diajukan": it["nilai_diajukan"],
             "dibayar": it["nilai_dibayar"], "status": STATUS.get(it["status"], it["status"]),
             "keterangan": keterangan(it, h["sbm"])} for it in h["items"]]
    uh = h["uang_harian"]
    rows.append({"uraian": f"Uang harian, {uh['hari']} hari × {rp(uh['tarif'])}", "bukti": "SPT",
                 "diajukan": uh["total"], "dibayar": uh["total"], "status": "Layak",
                 "keterangan": "Sesuai tarif provinsi tujuan, tanpa bukti"})
    if sum(r["dibayar"] for r in rows) != h["total_dibayar"] or sum(r["diajukan"] for r in rows) != h["total_diajukan"]:
        raise SystemExit("Jumlah rincian tidak sama dengan total hasil pemeriksaan. Dokumen tidak dibuat.")
    return rows


# ------------------------------------------------------------------ Excel

def tulis_xlsx(d: dict, rows: list[dict], path: Path) -> None:
    h, spt, sk = d["hasil"], d["spt"], d["satker"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Biaya"
    tipis = Side(style="thin", color="000000")
    kotak = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)
    f = lambda **k: Font(name=FONT, size=k.pop("size", 11), **k)  # noqa: E731
    lebar = {"A": 5, "B": 34, "C": 22, "D": 15, "E": 15, "F": 15, "G": 18, "H": 42}
    for col, w in lebar.items():
        ws.column_dimensions[col].width = w

    def judul(baris, teks, size=12, bold=True):
        ws.merge_cells(f"A{baris}:H{baris}")
        c = ws[f"A{baris}"]
        c.value, c.font, c.alignment = teks, f(size=size, bold=bold), Alignment(horizontal="center")

    judul(1, "PEMERINTAH KABUPATEN SEJAHTERA", 12)
    judul(2, sk["nama_satker"].upper(), 13)
    judul(3, sk["alamat"], 10, False)
    judul(5, "REKAPITULASI BIAYA PERJALANAN DINAS", 12)
    judul(6, f"Nomor SPJ: {d['nomor']}", 11, False)

    peg = h["pegawai"]
    identitas = [("Nama", peg["nama"]), ("NIP", peg["nip"]), ("Golongan", peg["golongan"]),
                 ("Maksud perjalanan", spt.get("maksud", "-")),
                 ("Tujuan", f"{spt.get('tujuan', '-')}, {spt.get('provinsi', '')}".strip(", ")),
                 ("Tanggal", rentang(spt["tanggal_berangkat"], spt["tanggal_kembali"])),
                 ("Dasar", spt["nomor_spt"])]
    r = 8
    for label, nilai in identitas:
        ws[f"B{r}"].value, ws[f"B{r}"].font = label, f()
        ws.merge_cells(f"C{r}:H{r}")
        ws[f"C{r}"].value, ws[f"C{r}"].font = f": {nilai}", f()
        r += 1

    r += 1
    kepala = ["No", "Uraian", "Bukti", "Diminta (Rp)", "Layak dibayar (Rp)", "Selisih (Rp)", "Status", "Keterangan"]
    for i, t in enumerate(kepala):
        c = ws.cell(row=r, column=i + 1, value=t)
        c.font, c.border = f(bold=True), kotak
        c.fill = PatternFill("solid", fgColor="D9D9D9")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    awal = r + 1
    for n, row in enumerate(rows, 1):
        r += 1
        nilai = [n, row["uraian"], row["bukti"], row["diajukan"], row["dibayar"], f"=D{r}-E{r}", row["status"],
                 row["keterangan"]]
        for i, v in enumerate(nilai):
            c = ws.cell(row=r, column=i + 1, value=v)
            c.font, c.border = f(), kotak
            c.alignment = Alignment(vertical="top", wrap_text=True,
                                    horizontal="center" if i in (0, 6) else ("right" if 3 <= i <= 5 else "left"))
            if 3 <= i <= 5:
                c.number_format = "#,##0"
    akhir = r
    r += 1
    ws.merge_cells(f"A{r}:C{r}")
    ws[f"A{r}"].value = "JUMLAH"
    for col, rumus in (("D", f"=SUM(D{awal}:D{akhir})"), ("E", f"=SUM(E{awal}:E{akhir})"), ("F", f"=D{r}-E{r}")):
        ws[f"{col}{r}"].value = rumus
        ws[f"{col}{r}"].number_format = "#,##0"
    for col in "ABCDEFGH":
        c = ws[f"{col}{r}"]
        c.font, c.border = f(bold=True), kotak
        c.alignment = Alignment(horizontal="center" if col == "A" else "right", vertical="center")
    r += 2
    ws.merge_cells(f"A{r}:H{r}")
    ws[f"A{r}"].value = f"Jumlah layak dibayar: {rp(h['total_dibayar'])} ({rupiah_terbilang(h['total_dibayar'])})"
    ws[f"A{r}"].font = f(bold=True)
    r += 1
    ws.merge_cells(f"A{r}:H{r}")
    ws[f"A{r}"].value = "Draf. Belum menjadi dasar pembayaran sebelum disetujui Bendahara Pengeluaran."
    ws[f"A{r}"].font = f(italic=True, size=10)
    r += 1
    ws.merge_cells(f"A{r}:H{r}")
    ws[f"A{r}"].value = "DATA FIKTIF UNTUK DEMO"
    ws[f"A{r}"].font = f(size=9, color="808080")

    ws.page_setup.orientation, ws.page_setup.paperSize = "landscape", ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws2 = wb.create_sheet("Hal yang Perlu Diperhatikan")
    for col, w in {"A": 5, "B": 28, "C": 18, "D": 60, "E": 26, "F": 40}.items():
        ws2.column_dimensions[col].width = w
    kepala2 = ["No", "Hal", "Tingkat", "Penjelasan", "Bukti", "Tindak lanjut"]
    for i, t in enumerate(kepala2):
        c = ws2.cell(row=1, column=i + 1, value=t)
        c.font, c.border = f(bold=True), kotak
        c.fill = PatternFill("solid", fgColor="D9D9D9")
        c.alignment = Alignment(horizontal="center", vertical="center")
    for n, t in enumerate(d["temuan"], 1):
        nilai = [n, HAL.get(t["aturan"], "Catatan"), TINGKAT.get(t["level"], t["level"]), penjelasan(t),
                 t.get("sumber") or "-", TINDAK.get(t["level"], "")]
        for i, v in enumerate(nilai):
            c = ws2.cell(row=n + 1, column=i + 1, value=v)
            c.font, c.border = f(), kotak
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if i in (0, 2) else "left")
    if not d["temuan"]:
        ws2.cell(row=2, column=2, value="Tidak ada hal yang perlu diperhatikan.").font = f()
    ws2.page_setup.orientation, ws2.page_setup.paperSize = "landscape", ws2.PAPERSIZE_A4
    ws2.page_setup.fitToWidth, ws2.page_setup.fitToHeight = 1, 0
    ws2.sheet_properties.pageSetUpPr.fitToPage = True
    wb.save(path)


# ------------------------------------------------------------------ Word

def _font(run, size=12, bold=False, italic=False):
    run.font.name, run.font.size, run.bold, run.italic = FONT, Pt(size), bold, italic
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def _p(doc, teks="", size=12, bold=False, italic=False, align=None, after=4):
    p = doc.add_paragraph()
    if teks:
        _font(p.add_run(teks), size, bold, italic)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.keep_with_next = bold
    if align:
        p.alignment = align
    return p


def _lebar(t, lebar):
    """Pasang lebar kolom tetap (Word dan LibreOffice membaca tblGrid, bukan hanya lebar sel)."""
    t.autofit = False
    for i, w in enumerate(lebar):
        t.columns[i].width = Cm(w)
        for sel in t.columns[i].cells:
            sel.width = Cm(w)
    for baris in t.rows:
        for sel in baris.cells:
            for p in sel.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(1)


def _tabel(doc, kepala, isi, lebar, kanan=(), tengah=(0,)):
    t = doc.add_table(rows=1, cols=len(kepala))
    t.style, t.alignment = "Table Grid", WD_TABLE_ALIGNMENT.CENTER
    for i, k in enumerate(kepala):
        sel = t.rows[0].cells[i]
        sel.text = ""
        _font(sel.paragraphs[0].add_run(k), 11, bold=True)
        sel.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for baris in isi:
        sel = t.add_row().cells
        for i, v in enumerate(baris):
            sel[i].text = ""
            _font(sel[i].paragraphs[0].add_run(str(v)), 11)
            if i in kanan:
                sel[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif i in tengah:
                sel[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _lebar(t, lebar)
    return t


def tulis_docx(d: dict, rows: list[dict], path: Path) -> None:
    h, spt, sk = d["hasil"], d["spt"], d["satker"]
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    for s in doc.sections:
        s.page_height, s.page_width = Cm(29.7), Cm(21)
        s.top_margin = s.bottom_margin = Cm(2)
        s.left_margin, s.right_margin = Cm(2.5), Cm(2)

    c = WD_ALIGN_PARAGRAPH.CENTER
    _p(doc, "PEMERINTAH KABUPATEN SEJAHTERA", 12, True, align=c, after=0)
    _p(doc, sk["nama_satker"].upper(), 13, True, align=c, after=0)
    _p(doc, f"{sk['alamat']} · Telp. {sk['telepon']}", 10, align=c, after=2)
    garis = doc.add_paragraph()
    garis.paragraph_format.space_after = Pt(10)
    pbdr = garis._p.get_or_add_pPr()
    from docx.oxml import OxmlElement
    b = OxmlElement("w:pBdr")
    bawah = OxmlElement("w:bottom")
    for k, v in (("w:val", "double"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "000000")):
        bawah.set(qn(k), v)
    b.append(bawah)
    pbdr.append(b)

    _p(doc, "RINGKASAN PEMERIKSAAN", 12, True, align=c, after=0)
    _p(doc, "SURAT PERTANGGUNGJAWABAN PERJALANAN DINAS", 12, True, align=c, after=0)
    _p(doc, f"Nomor: {d['nomor']}", 12, align=c, after=12)

    peg = h["pegawai"]
    _p(doc, "A. Data Pegawai dan Perjalanan", bold=True)
    data = [("Nama", peg["nama"]), ("NIP", peg["nip"]), ("Golongan", peg["golongan"]),
            ("Maksud perjalanan", spt.get("maksud", "-")),
            ("Tujuan", f"{spt.get('tujuan', '-')}, {spt.get('provinsi', '')}".strip(", ")),
            ("Tanggal", f"{rentang(spt['tanggal_berangkat'], spt['tanggal_kembali'])} ({spt.get('lama_hari', h['uang_harian']['hari'])} hari)"),
            ("Dasar penugasan", spt["nomor_spt"])]
    t = doc.add_table(rows=0, cols=3)
    for label, nilai in data:
        sel = t.add_row().cells
        for i, v in enumerate((label, ":", nilai)):
            sel[i].text = ""
            _font(sel[i].paragraphs[0].add_run(v), 12)
    _lebar(t, (4.5, 0.5, 11.5))
    _p(doc, after=6)

    _p(doc, "B. Rincian Biaya", bold=True)
    isi = [[n, r["uraian"], rp(r["diajukan"]), rp(r["dibayar"]), r["keterangan"]] for n, r in enumerate(rows, 1)]
    isi.append(["", "Jumlah", rp(h["total_diajukan"]), rp(h["total_dibayar"]), ""])
    tb = _tabel(doc, ["No", "Uraian", "Diminta", "Layak dibayar", "Keterangan"], isi, (1, 5.5, 2.8, 2.8, 4.4),
                kanan=(2, 3))
    for sel in tb.rows[-1].cells:
        for run in sel.paragraphs[0].runs:
            run.bold = True
    _p(doc, after=2)
    _p(doc, f"Jumlah layak dibayar: {rp(h['total_dibayar'])}", bold=True, after=0)
    _p(doc, f"({rupiah_terbilang(h['total_dibayar'])})", italic=True, after=10)

    _p(doc, "C. Hal yang Perlu Diperhatikan", bold=True)
    if d["temuan"]:
        isi = [[n, HAL.get(t["aturan"], "Catatan"), TINGKAT.get(t["level"], t["level"]), penjelasan(t),
                TINDAK.get(t["level"], "")] for n, t in enumerate(d["temuan"], 1)]
        _tabel(doc, ["No", "Hal", "Tingkat", "Penjelasan", "Tindak lanjut"], isi, (1, 3.2, 2.4, 6.5, 3.4))
    else:
        _p(doc, "Tidak ada hal yang perlu diperhatikan.")
    _p(doc, after=10)

    _p(doc, "D. Pemeriksaan Berkas Fisik oleh Bendahara", bold=True)
    _p(doc, "Bagian ini tidak dapat diperiksa dari salinan digital.", 11, italic=True, after=4)
    fisik = ["SPPD sudah ditandatangani dan dicap pejabat di tempat tujuan",
             "Bukti asli sudah diterima, bukan hanya foto atau salinan",
             "Laporan perjalanan dinas sudah dilampirkan"]
    if h["total_dibayar"] > 5_000_000:
        fisik.append("Kuitansi bernilai di atas Rp5.000.000 sudah bermeterai Rp10.000")
    for teks in fisik:
        _p(doc, "☐  " + teks, after=2)
    _p(doc, after=8)

    _p(doc, "E. Keputusan Bendahara", bold=True)
    _p(doc, "☐  Disetujui untuk dibayarkan sebesar " + rp(h["total_dibayar"]), after=2)
    _p(doc, "☐  Ditolak, dengan alasan: ........................................................................", after=14)

    ttd = doc.add_table(rows=1, cols=2)
    kiri = ["Disiapkan oleh,", "Pengelola SPJ", "", "", "", "(.................................)"]
    kanan = [f"Kota Sejahtera, ....................... {date.today().year}", "Bendahara Pengeluaran", "", "", "",
             sk["bendahara"]["nama"], f"NIP {sk['bendahara']['nip']}"]
    for sel, baris in ((ttd.rows[0].cells[0], kiri), (ttd.rows[0].cells[1], kanan)):
        sel.text = ""
        for i, teks in enumerate(baris):
            p = sel.paragraphs[0] if i == 0 else sel.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            if teks:
                _font(p.add_run(teks), 12, bold=teks == sk["bendahara"]["nama"])

    _p(doc, after=12)
    _p(doc, "Ringkasan ini disusun dengan bantuan sistem pemeriksaan otomatis dan belum menjadi dasar pembayaran "
            "sebelum disetujui Bendahara Pengeluaran.", 9, italic=True, after=0)
    _p(doc, "DATA FIKTIF UNTUK DEMO", 9, after=0)
    doc.save(path)


# ------------------------------------------------------------------ HTML

def tulis_html(d: dict, rows: list[dict], path: Path) -> None:
    h, spt, sk = d["hasil"], d["spt"], d["satker"]
    e = html.escape
    peg = h["pegawai"]
    baris = "".join(
        f"<tr><td class=c>{n}</td><td>{e(r['uraian'])}</td><td class=r>{rp(r['diajukan'])}</td>"
        f"<td class=r>{rp(r['dibayar'])}</td><td>{e(r['status'])}</td><td>{e(r['keterangan'])}</td></tr>"
        for n, r in enumerate(rows, 1))
    if d["temuan"]:
        hal = "".join(
            f"<tr class='t-{t['level'].lower()}'><td class=c>{n}</td><td>{e(HAL.get(t['aturan'], 'Catatan'))}</td>"
            f"<td>{e(TINGKAT.get(t['level'], t['level']))}</td><td>{e(penjelasan(t))}</td>"
            f"<td>{e(TINDAK.get(t['level'], ''))}</td></tr>" for n, t in enumerate(d["temuan"], 1))
        hal = (f"<table><thead><tr><th>No</th><th>Hal</th><th>Tingkat</th><th>Penjelasan</th><th>Tindak lanjut</th>"
               f"</tr></thead><tbody>{hal}</tbody></table>")
    else:
        hal = "<p>Tidak ada hal yang perlu diperhatikan.</p>"
    halaman = f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d['nomor'])} – Ringkasan Pemeriksaan</title>
<style>
body{{font-family:"Times New Roman",Times,serif;font-size:16px;color:#000;background:#f4f4f4;margin:0;padding:24px 12px}}
.kertas{{max-width:820px;margin:0 auto;background:#fff;padding:32px 40px;border:1px solid #ccc}}
.kop{{text-align:center;border-bottom:3px double #000;padding-bottom:8px;margin-bottom:16px}}
.kop b{{display:block}} .kop small{{font-size:13px}}
h1{{font-size:17px;text-align:center;margin:0}} .nomor{{text-align:center;margin:2px 0 18px}}
h2{{font-size:16px;margin:22px 0 8px}}
table{{width:100%;border-collapse:collapse;font-size:15px}}
th,td{{border:1px solid #000;padding:5px 7px;vertical-align:top}} th{{background:#e6e6e6}}
.data td{{border:none;padding:2px 4px}} .data td:first-child{{width:170px}}
.c{{text-align:center}} .r{{text-align:right;white-space:nowrap}} tfoot td{{font-weight:bold}}
.t-kritis td{{background:#fbe5e1}} .t-tinggi td{{background:#fdf1dc}}
.bayar{{margin-top:10px;font-weight:bold}} .catatan{{font-size:13px;font-style:italic;margin-top:24px}}
</style></head><body><div class="kertas">
<div class="kop"><b>PEMERINTAH KABUPATEN SEJAHTERA</b><b>{e(sk['nama_satker'].upper())}</b><small>{e(sk['alamat'])}</small></div>
<h1>RINGKASAN PEMERIKSAAN<br>SURAT PERTANGGUNGJAWABAN PERJALANAN DINAS</h1>
<p class="nomor">Nomor: {e(d['nomor'])}</p>
<h2>A. Data Pegawai dan Perjalanan</h2>
<table class="data">
<tr><td>Nama</td><td>: {e(peg['nama'])}</td></tr><tr><td>NIP</td><td>: {e(peg['nip'])}</td></tr>
<tr><td>Golongan</td><td>: {e(peg['golongan'])}</td></tr><tr><td>Maksud perjalanan</td><td>: {e(spt.get('maksud', '-'))}</td></tr>
<tr><td>Tujuan</td><td>: {e(spt.get('tujuan', '-'))}, {e(spt.get('provinsi', ''))}</td></tr>
<tr><td>Tanggal</td><td>: {e(rentang(spt['tanggal_berangkat'], spt['tanggal_kembali']))}</td></tr>
<tr><td>Dasar penugasan</td><td>: {e(spt['nomor_spt'])}</td></tr></table>
<h2>B. Rincian Biaya</h2>
<table><thead><tr><th>No</th><th>Uraian</th><th>Diminta</th><th>Layak dibayar</th><th>Status</th><th>Keterangan</th></tr></thead>
<tbody>{baris}</tbody><tfoot><tr><td></td><td>Jumlah</td><td class=r>{rp(h['total_diajukan'])}</td>
<td class=r>{rp(h['total_dibayar'])}</td><td colspan=2></td></tr></tfoot></table>
<p class="bayar">Jumlah layak dibayar: {rp(h['total_dibayar'])}<br><i>({e(rupiah_terbilang(h['total_dibayar']))})</i></p>
<h2>C. Hal yang Perlu Diperhatikan</h2>{hal}
<p class="catatan">Keputusan ada pada Bendahara Pengeluaran di Meja Pimpinan. Ringkasan ini disusun dengan bantuan
sistem pemeriksaan otomatis dan belum menjadi dasar pembayaran. DATA FIKTIF UNTUK DEMO.</p>
</div></body></html>
"""
    path.write_text(halaman, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"kasus-\d{3}[a-z]?", sys.argv[1]):
        raise SystemExit(__doc__)
    d = muat(sys.argv[1])
    rows = baris_biaya(d)
    folder = BASE / "keluar" / "draf" / d["nomor"]
    folder.mkdir(parents=True, exist_ok=True)
    tulis_xlsx(d, rows, folder / "rekap.xlsx")
    tulis_docx(d, rows, folder / "draf_spj.docx")
    tulis_html(d, rows, folder / "layar_konfirmasi.html")
    (folder / "timeline.json").write_text(json.dumps({"timeline": d["timeline"]}, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    spt, h = d["spt"], d["hasil"]
    tersisip = [it["perintah_tersisip"] for it in h["items"] if it.get("perintah_tersisip")]
    print(json.dumps({
        "nomor": d["nomor"], "pegawai": h["pegawai"]["nama"], "tujuan": spt.get("tujuan", ""),
        "tanggal_spt": f"{spt['tanggal_berangkat']} s.d. {spt['tanggal_kembali']}",
        "total_diajukan": h["total_diajukan"], "total_dibayar": h["total_dibayar"],
        "temuan": [{k: t.get(k) for k in ("level", "aturan", "deskripsi", "sumber")} for t in d["temuan"]],
        "perintah_tersisip": tersisip,
        "berkas": sorted(p.name for p in folder.iterdir()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
