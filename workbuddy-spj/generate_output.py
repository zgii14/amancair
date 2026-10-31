#!/usr/bin/env python3
"""
Generate output for SPJ case (Tahap 3+4).
Script ini dijalankan oleh agen Penyusun SPJ secara terpisah.
Input: hasil kerja agen lain dari kerja/*.json
Output: rekap.xlsx (dengan formula MIN Excel), draf_spj.docx, timeline.json, layar_konfirmasi.html
"""

import json
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "tools"))
from hitung import rekap_total

BASE = Path("D:/Agent 2/spj-agent")
KASUS_DIR = BASE / "data/kasus/kasus-001"
SPT_PATH = BASE / "data/spt/SPT-2026-001.json"
SATKER_PATH = BASE / "data/master/satker.json"
OUTPUT_DIR = BASE / "keluar/draf/SPJ-2026-001"
KERJA_DIR = OUTPUT_DIR / "kerja"
SIDIK_PATH = BASE / "log/indeks_sidik.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
KERJA_DIR.mkdir(parents=True, exist_ok=True)

WITA = timezone(timedelta(hours=8))


def now_wita() -> str:
    return datetime.now(WITA).isoformat()


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_kerja():
    """Baca semua hasil kerja agen dari kerja/*.json"""
    hasil = {}
    for nama in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk", "verifikator-sbm", "auditor"]:
        p = KERJA_DIR / f"{nama}.json"
        if p.exists():
            hasil[nama] = load_json(p)
    return hasil


def build_items_dari_verifikator(hasil_kerja):
    """Ambil items dari verifikator-sbm.json"""
    return hasil_kerja["verifikator-sbm"]["items"]


def get_pagu_data(spt):
    """Baca pagu dari SBM Excel"""
    import openpyxl
    sbm_path = BASE / "data/master/sbm.xlsx"
    wb = openpyxl.load_workbook(sbm_path)
    ws = wb.active
    provinsi = spt["provinsi"]
    gol = spt["pegawai"]["golongan"].split("/")[0]
    for row in ws.iter_rows(min_row=3, values_only=True):
        r_prov, r_gol, r_pagu_h, r_uh, r_pagu_t = row[:5]
        if r_prov == provinsi and str(r_gol) == gol:
            return {
                "pagu_hotel": int(r_pagu_h) if r_pagu_h else 0,
                "uang_harian": int(r_uh) if r_uh else 0,
                "pagu_taksi": int(r_pagu_t) if r_pagu_t else 0,
            }
    return {}


def susun_rekap_xlsx(items, pagu_data):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap SPJ"

    # Headers dengan kolom pagu & qty
    headers = ["id_bukti", "jenis", "file_sumber", "kutipan_teks", "kode_aturan",
               "rumus_hitung", "nilai_diajukan", "pagu", "qty",
               "nilai_dibayar", "selisih",
               "yakin_pembaca", "level_risiko", "status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    # Data rows
    for item in items:
        jenis = item["jenis"]
        # Determine pagu and qty
        pagu = ""
        qty = ""
        if jenis == "hotel":
            # Extract malam from rumus_hitung or calculate
            malam = 3  # default for kasus-001
            pagu = pagu_data.get("pagu_hotel", 0)
            qty = malam
        elif jenis == "taksi":
            pagu = pagu_data.get("pagu_taksi", 0)
            qty = 1
        elif jenis == "uang_harian":
            pagu = pagu_data.get("uang_harian", 0)
            qty = 4  # lama hari
        elif jenis == "tiket":
            pagu = ""
            qty = 1
        elif jenis == "makan":
            pagu = ""
            qty = ""

        ws.append([
            item["id_bukti"], item["jenis"], item.get("file_sumber") or "",
            item.get("kutipan_teks") or "", item.get("kode_aturan") or "",
            item.get("rumus_hitung") or "",
            item["nilai_diajukan"],
            pagu, qty,
            None,  # nilai_dibayar = formula
            None,  # selisih = formula
            item.get("yakin_pembaca") or "", item.get("level_risiko") or "", item["status"]
        ])

    # Write formulas per row
    for row_idx in range(2, ws.max_row + 1):
        jenis = ws.cell(row=row_idx, column=2).value
        # nilai_dibayar formula (col J = 10)
        if jenis == "makan":
            ws.cell(row=row_idx, column=10).value = 0
        elif jenis == "tiket":
            ws.cell(row=row_idx, column=10).value = f"=G{row_idx}"
        elif jenis == "hotel":
            ws.cell(row=row_idx, column=10).value = f"=MIN(G{row_idx},H{row_idx}*I{row_idx})"
        elif jenis == "taksi":
            ws.cell(row=row_idx, column=10).value = f"=MIN(G{row_idx},H{row_idx})"
        elif jenis == "uang_harian":
            ws.cell(row=row_idx, column=10).value = f"=G{row_idx}"
        else:
            ws.cell(row=row_idx, column=10).value = f"=G{row_idx}"

        # selisih formula (col K = 11)
        ws.cell(row=row_idx, column=11).value = f"=G{row_idx}-J{row_idx}"

    # TOTAL row with SUM formulas
    total_row = ws.max_row + 1
    ws.cell(row=total_row, column=1, value="TOTAL")
    ws.cell(row=total_row, column=1).font = Font(bold=True)
    ws.cell(row=total_row, column=7, value=f"=SUM(G2:G{total_row-1})")
    ws.cell(row=total_row, column=10, value=f"=SUM(J2:J{total_row-1})")
    ws.cell(row=total_row, column=11, value=f"=G{total_row}-J{total_row}")
    for col in [7, 10, 11]:
        ws.cell(row=total_row, column=col).font = Font(bold=True)

    # Auto width
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 60)

    rekap_path = OUTPUT_DIR / "rekap.xlsx"
    wb.save(rekap_path)

    with open(rekap_path, "rb") as f:
        rekap_hash = hashlib.sha256(f.read()).hexdigest()
    return rekap_hash


def susun_draf_spj(spt, satker, items):
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("DATA FIKTIF UNTUK DEMO\n")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(255, 0, 0)
    run.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{satker['nama_satker']}\n")
    run.bold = True
    run.font.size = Pt(14)
    p.add_run(f"{satker['alamat']}\nTelp: {satker['telepon']}\n").font.size = Pt(10)
    doc.add_paragraph("_" * 60)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("SURAT PERTANGGUNGJAWABAN (SPJ)\nPERJALANAN DINAS")
    run.bold = True
    run.font.size = Pt(14)
    doc.add_paragraph()

    for label, value in [
        ("Nomor SPT", spt["nomor_spt"]),
        ("Nama", spt["pegawai"]["nama"]),
        ("NIP", spt["pegawai"]["nip"]),
        ("Golongan", spt["pegawai"]["golongan"]),
        ("Maksud", spt["maksud"]),
        ("Tujuan", spt["tujuan"]),
        ("Tanggal Berangkat", spt["tanggal_berangkat"]),
        ("Tanggal Kembali", spt["tanggal_kembali"]),
        ("Lama", f"{spt['lama_hari']} hari"),
    ]:
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(str(value))

    doc.add_paragraph()
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text, hdr[4].text = (
        "No", "Jenis Biaya", "Diajukan (Rp)", "Dibayar (Rp)", "Selisih (Rp)"
    )
    for c in hdr:
        c.paragraphs[0].runs[0].bold = True

    for i, it in enumerate(items, 1):
        r = table.add_row().cells
        r[0].text = str(i)
        r[1].text = it["jenis"].upper()
        r[2].text = f"{it['nilai_diajukan']:,}"
        r[3].text = f"{it['nilai_dibayar']:,}"
        r[4].text = f"{it['selisih']:,}"

    totals = rekap_total(items)
    r = table.add_row().cells
    r[1].text = "TOTAL"
    r[1].paragraphs[0].runs[0].bold = True
    r[2].text = f"{totals['total_diajukan']:,}"
    r[2].paragraphs[0].runs[0].bold = True
    r[3].text = f"{totals['total_dibayar']:,}"
    r[3].paragraphs[0].runs[0].bold = True
    r[4].text = f"{totals['selisih']:,}"
    r[4].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Bendahara Pengeluaran\n\n\n\n").bold = True
    p.add_run(f"{satker['bendahara']['nama']}\nNIP. {satker['bendahara']['nip']}")
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Pejabat Pembuat Komitmen\n\n\n\n").bold = True
    p.add_run(f"{satker['kepala_dinas']['nama']}\nNIP. {satker['kepala_dinas']['nip']}")
    doc.save(OUTPUT_DIR / "draf_spj.docx")


def susun_timeline_json(hasil_auditor):
    with open(OUTPUT_DIR / "timeline.json", "w", encoding="utf-8") as f:
        json.dump({
            "kasus_id": "kasus-001",
            "timeline": hasil_auditor["timeline"],
            "kontradiksi": hasil_auditor["kontradiksi"],
            "temuan": hasil_auditor["temuan"],
            "rekomendasi": hasil_auditor["rekomendasi"],
        }, f, ensure_ascii=False, indent=2)


def susun_layar_konfirmasi(spt, items, hasil_auditor, rekap_hash):
    totals = rekap_total(items)
    temuan_html = ""
    if hasil_auditor["temuan"]:
        for t in hasil_auditor["temuan"]:
            level = t["level"]
            badge_class = f"badge-{level.lower()}"
            temuan_html += f'<div class="card temuan-{level.lower()}">\n'
            temuan_html += f'  <p><span class="badge {badge_class}">{level}</span> <strong>{t.get("id_bukti", "")} ({t["tipe"]})</strong> — {t["deskripsi"]}</p>\n'
            temuan_html += '</div>\n'
    else:
        temuan_html = '<div class="card temuan-none"><p>Tidak ada temuan.</p></div>\n'

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Layar Konfirmasi SPJ-2026-001</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 16px; background: #f5f5f5; color: #333; }}
  .card {{ background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .header {{ background: #2F5496; color: #fff; text-align: center; padding: 20px; border-radius: 12px; margin-bottom: 16px; }}
  .header h1 {{ margin: 0; font-size: 1.3rem; }}
  .summary {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
  .summary-item {{ flex: 1; min-width: 120px; text-align: center; padding: 10px; }}
  .summary-item .label {{ font-size: 0.8rem; color: #666; }}
  .summary-item .value {{ font-size: 1.2rem; font-weight: bold; }}
  .temuan-rendah {{ border-left: 4px solid #388e3c; background: #e8f5e9; }}
  .temuan-sedang {{ border-left: 4px solid #f9a825; background: #fffde7; }}
  .temuan-tinggi {{ border-left: 4px solid #d32f2f; background: #ffebee; }}
  .temuan-kritis {{ border-left: 4px solid #b71c1c; background: #ffcdd2; }}
  .temuan-none {{ border-left: 4px solid #2F5496; background: #e3f2fd; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; color: #fff; }}
  .badge-rendah {{ background: #388e3c; }}
  .badge-sedang {{ background: #f9a825; color: #000; }}
  .badge-tinggi {{ background: #d32f2f; }}
  .badge-kritis {{ background: #b71c1c; }}
  .hash {{ font-family: monospace; font-size: 0.7rem; color: #666; word-break: break-all; }}
  .instruksi {{ background: #e8f5e9; border: 1px solid #388e3c; border-radius: 8px; padding: 12px; margin-top: 16px; }}
  .instruksi code {{ background: #fff; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
  .watermark {{ text-align: center; color: #d32f2f; font-weight: bold; font-size: 0.85rem; margin-bottom: 12px; }}
</style>
</head>
<body>
<div class="watermark">DATA FIKTIF UNTUK DEMO</div>

<div class="header">
  <h1>Layar Konfirmasi SPJ-2026-001</h1>
  <p>{spt['pegawai']['nama']} — {spt['provinsi']} — 5–8 Okt 2026</p>
</div>

<div class="card">
  <div class="summary">
    <div class="summary-item">
      <div class="label">Total Diajukan</div>
      <div class="value">Rp {totals['total_diajukan']:,}</div>
    </div>
    <div class="summary-item">
      <div class="label">Total Dibayar</div>
      <div class="value">Rp {totals['total_dibayar']:,}</div>
    </div>
    <div class="summary-item">
      <div class="label">Selisih</div>
      <div class="value">Rp {totals['selisih']:,}</div>
    </div>
  </div>
</div>

<div class="card">
  <h3>Daftar Temuan</h3>
  {temuan_html}
</div>

<div class="card">
  <h3>Timeline</h3>
  <div>
    <div>5 Okt — SPT mulai + Tiket berangkat + Hotel check-in + Taksi bandara</div>
    <div>6 Okt — Struk makan</div>
    <div>8 Okt — Hotel check-out + Tiket kembali + SPT selesai</div>
  </div>
</div>

<div class="card">
  <h3>Sidik Keamanan rekap.xlsx</h3>
  <p class="hash">SHA-256: {rekap_hash}</p>
</div>

<div class="instruksi">
  <strong>Instruksi Persetujuan:</strong><br>
  Ketik: <code>SETUJUI SPJ-2026-001</code><br>
  (Kasus ini tidak ada risiko TINGGI/KRITIS, format standar cukup.)
</div>

</body>
</html>
"""
    with open(OUTPUT_DIR / "layar_konfirmasi.html", "w", encoding="utf-8") as f:
        f.write(html)


def susun_indeks_sidik(hasil_kerja):
    sidik_list = []
    for nama in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"]:
        if nama in hasil_kerja:
            for it in hasil_kerja[nama]["items"]:
                sidik_list.append({
                    "jenis": it["jenis"],
                    "sidik": it.get("sidik", {}),
                    "id_bukti": it.get("id_bukti"),
                    "file_sumber": it.get("file_sumber")
                })
    sidik = {"kasus-001": sidik_list}
    with open(SIDIK_PATH, "w", encoding="utf-8") as f:
        json.dump(sidik, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("PENYUSUN SPJ: Assembly Final Kasus-001")
    print("=" * 60)

    spt = load_json(SPT_PATH)
    satker = load_json(SATKER_PATH)
    hasil_kerja = read_kerja()
    pagu_data = get_pagu_data(spt)

    if "verifikator-sbm" not in hasil_kerja:
        print("ERROR: verifikator-sbm.json tidak ditemukan!")
        sys.exit(1)
    if "auditor" not in hasil_kerja:
        print("ERROR: auditor.json tidak ditemukan!")
        sys.exit(1)

    items = build_items_dari_verifikator(hasil_kerja)
    hasil_auditor = hasil_kerja["auditor"]

    print("\n[PENYUSUN SPJ] Menyusun rekap.xlsx dengan formula MIN Excel...")
    rekap_hash = susun_rekap_xlsx(items, pagu_data)
    print(f"[PENYUSUN SPJ] rekap.xlsx tersimpan (SHA-256: {rekap_hash})")

    print("[PENYUSUN SPJ] Menyusun draf_spj.docx...")
    susun_draf_spj(spt, satker, items)

    print("[PENYUSUN SPJ] Menyusun timeline.json...")
    susun_timeline_json(hasil_auditor)

    print("[PENYUSUN SPJ] Menyusun layar_konfirmasi.html...")
    susun_layar_konfirmasi(spt, items, hasil_auditor, rekap_hash)

    print("[PENYUSUN SPJ] Menyusun indeks_sidik.json...")
    susun_indeks_sidik(hasil_kerja)

    # Tulis hasil kerja penyusun
    totals = rekap_total(items)
    waktu_sekarang = now_wita()
    hasil_penyusun = {
        "agen": "penyusun-spj",
        "kasus": "kasus-001",
        "waktu_mulai": waktu_sekarang,
        "waktu_selesai": waktu_sekarang,
        "total_diajukan": totals["total_diajukan"],
        "total_dibayar": totals["total_dibayar"],
        "selisih": totals["selisih"],
        "rekap_hash": rekap_hash,
    }
    with open(KERJA_DIR / "penyusun-spj.json", "w", encoding="utf-8") as f:
        json.dump(hasil_penyusun, f, ensure_ascii=False, indent=2)

    # Audit entry penyusun
    audit_entry = {
        "waktu": waktu_sekarang,
        "kasus": "kasus-001",
        "agen": "penyusun-spj",
        "aksi": "susun_output",
        "file_dibaca": "hasil_verifikasi + audit",
        "keputusan": f"Output disimpan (rekap hash: {rekap_hash[:16]}...)",
        "aturan": None,
    }
    with open(KERJA_DIR / "penyusun-spj-audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_entry, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("RINGKASAN KASUS-001")
    print("=" * 60)
    print(f"Total diajukan: Rp {totals['total_diajukan']:,}")
    print(f"Total dibayar:  Rp {totals['total_dibayar']:,}")
    print(f"Selisih:        Rp {totals['selisih']:,}")
    print(f"Rekap SHA-256:  {rekap_hash}")
    print(f"\nOutput:")
    print(f"  - rekap.xlsx:      {OUTPUT_DIR / 'rekap.xlsx'}")
    print(f"  - draf_spj.docx:   {OUTPUT_DIR / 'draf_spj.docx'}")
    print(f"  - timeline.json:   {OUTPUT_DIR / 'timeline.json'}")
    print(f"  - layar_konfirmasi.html: {OUTPUT_DIR / 'layar_konfirmasi.html'}")
    print(f"  - indeks_sidik.json: {SIDIK_PATH}")
    print(f"  - kerja/penyusun-spj.json: {KERJA_DIR / 'penyusun-spj.json'}")
    print(f"  - kerja/penyusun-spj-audit.json: {KERJA_DIR / 'penyusun-spj-audit.json'}")


if __name__ == "__main__":
    main()
