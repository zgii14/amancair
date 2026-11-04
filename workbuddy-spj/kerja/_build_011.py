# -*- coding: utf-8 -*-
import json, os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE = r"D:/Agent 2/spj-agent"
OUT = os.path.join(BASE, "keluar/draf/SPJ-2026-011")
os.makedirs(OUT, exist_ok=True)

hasil = json.load(open(os.path.join(BASE, "kerja/verifikator-sbm_kasus-011.json"), encoding="utf-8"))["hasil"]
aud = json.load(open(os.path.join(BASE, "kerja/auditor_kasus-011.json"), encoding="utf-8"))

kutipan, yakin = {}, {}
for f in ["pembaca-tiket_kasus-011.json", "pembaca-struk_kasus-011.json"]:
    d = json.load(open(os.path.join(BASE, "kerja", f), encoding="utf-8"))
    for it in d["item_bukti"]:
        kutipan[it["id"]] = it["kutipan"]
        yakin[it["id"]] = it["yakin"]

def rp(n):
    return "Rp " + format(n, ",d").replace(",", ".")

# ---------------- rekap.xlsx ----------------
wb = Workbook()
ws = wb.active
ws.title = "rekap"
headers = ["id_bukti", "jenis", "file_sumber", "kutipan_teks", "kode_aturan", "rumus_hitung",
           "nilai_diajukan", "nilai_dibayar", "selisih", "yakin_pembaca", "level_risiko", "status"]
ws.append(headers)

meta = {
    "B01": ("-", "Dibayar sesuai bukti", "-", "sesuai"),
    "B02": ("R06", "Sudah diajukan di SPJ-2026-001 (R06 lintas SPJ)", "KRITIS", "ditahan"),
}
r = 2
for it in hasil["items"]:
    ka, rumus, risiko, status = meta[it["id"]]
    ws.append([it["id"], it["jenis"], it["file"], kutipan.get(it["id"], ""), ka, rumus,
               it["nilai_diajukan"], it["nilai_dibayar"], f"=G{r}-H{r}",
               yakin.get(it["id"], "-"), risiko, status])
    r += 1

uh = hasil["uang_harian"]
ws.append(["uang_harian", "uang_harian", "SBM DKI Jakarta golongan III (periksa_aturan)",
           f"Uang harian {uh['hari']} hari x {rp(uh['tarif'])}",
           "R04", f"{uh['hari']} hari x {rp(uh['tarif'])}", uh["total"], uh["total"],
           f"=G{r}-H{r}", "-", "-", "sesuai"])
r += 1

# Baris TOTAL: tepat di bawah item terakhir, kolom lain None
ws.append(["TOTAL", None, None, None, None, None,
           "=SUM(G2:G4)", "=SUM(H2:H4)", "=G5-H5",
           None, None, None])

hdr_fill = PatternFill("solid", fgColor="1F3864")
thin = Side(style="thin", color="D9D9D9")
for c in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=c)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = hdr_fill
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for row in ws.iter_rows(min_row=2, max_row=5, max_col=len(headers)):
    for cell in row:
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        cell.alignment = Alignment(vertical="top", wrap_text=(cell.column == 4))
        if cell.column in (7, 8, 9):
            cell.number_format = '#,##0'
for c in range(1, len(headers) + 1):
    ws.cell(row=5, column=c).font = Font(bold=True)
    ws.cell(row=5, column=c).fill = PatternFill("solid", fgColor="F1F5FB")
widths = [12, 12, 34, 58, 12, 38, 15, 15, 12, 13, 12, 12]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = "A2"
wb.save(os.path.join(OUT, "rekap.xlsx"))

# ---------------- timeline.json ----------------
json.dump(aud["timeline"], open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ---------------- layar_konfirmasi.html ----------------
ORDER = {"KRITIS": 0, "TINGGI": 1, "SEDANG": 2, "RENDAH": 3}
temuan = sorted(hasil["temuan"], key=lambda t: ORDER.get(t["level"].upper(), 9))

rows = ""
for it in hasil["items"]:
    st = it["status"].upper()
    cls = "hold" if st == "DITAHAN" else "ok"
    rows += f"""      <tr>
        <td class="mono">{it['id']}</td>
        <td>{it['jenis']}</td>
        <td>{kutipan.get(it['id'], '')}</td>
        <td class="num">{rp(it['nilai_diajukan'])}</td>
        <td class="num">{rp(it['nilai_dibayar'])}</td>
        <td><span class="badge {cls}">{st}</span></td>
      </tr>
"""
rows += f"""      <tr class="sub">
        <td class="mono">UH</td>
        <td>uang harian</td>
        <td>{uh['hari']} hari x {rp(uh['tarif'])} (R04)</td>
        <td class="num">{rp(uh['total'])}</td>
        <td class="num">{rp(uh['total'])}</td>
        <td><span class="badge ok">SESUAI</span></td>
      </tr>
"""

tlis = ""
for t in temuan:
    cls = t["level"].lower()
    tlis += f"""      <li class="temuan {cls}">
        <div class="tlevel">[{t['level'].upper()}] {t['aturan']}</div>
        <div class="tdesc">{t['deskripsi']}</div>
        <div class="tsrc">sumber: {t['sumber'] if t['sumber'] else '-'}</div>
      </li>
"""

html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Layar Konfirmasi SPJ-2026-011</title>
<style>
  :root {{ --ink:#1b2430; --mut:#64748b; --line:#e2e8f0; --bg:#f6f8fb; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:32px; background:var(--bg); color:var(--ink);
         font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif; font-size:14px; }}
  .card {{ max-width:980px; margin:0 auto; background:#fff; border:1px solid var(--line);
           border-radius:14px; box-shadow:0 8px 28px rgba(15,23,42,.06); overflow:hidden; }}
  header {{ padding:24px 28px; background:#1f3864; color:#fff; }}
  header .eyebrow {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; opacity:.75; }}
  header h1 {{ margin:6px 0 2px; font-size:22px; }}
  header .sub {{ opacity:.85; font-size:13px; }}
  .body {{ padding:24px 28px 28px; }}
  .meta {{ display:grid; grid-template-columns:repeat(2,1fr); gap:10px 28px; margin-bottom:22px; }}
  .meta div {{ display:flex; justify-content:space-between; gap:12px; padding:8px 0; border-bottom:1px dashed var(--line); }}
  .meta span:first-child {{ color:var(--mut); }}
  .meta span:last-child {{ font-weight:600; text-align:right; }}
  h2 {{ font-size:14px; letter-spacing:.06em; text-transform:uppercase; color:var(--mut);
        margin:26px 0 10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; padding:9px 10px; background:#eef2f8; color:#334155;
        font-size:11px; text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid var(--line); }}
  td {{ padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  td.num {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }}
  tr.sub td {{ background:#fafbfd; color:#475569; }}
  tr.total td {{ font-weight:700; background:#f1f5fb; border-top:2px solid #1f3864; }}
  .mono {{ font-family:Consolas,monospace; font-size:12px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; }}
  .badge.ok {{ background:#dcfce7; color:#166534; }}
  .badge.hold {{ background:#fee2e2; color:#991b1b; }}
  .totals {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:18px; }}
  .tbox {{ border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .tbox .lbl {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--mut); }}
  .tbox .val {{ font-size:20px; font-weight:700; margin-top:4px; font-variant-numeric:tabular-nums; }}
  .tbox.pay {{ background:#eef6ff; border-color:#bfdbfe; }}
  ul.temuan-list {{ list-style:none; margin:0; padding:0; }}
  li.temuan {{ border-left:4px solid #cbd5e1; background:#fbfcfe; padding:12px 14px; margin-bottom:10px; border-radius:0 8px 8px 0; }}
  li.kritis {{ border-left-color:#7f1d1d; background:#fef2f2; }}
  li.tinggi {{ border-left-color:#dc2626; background:#fef4f4; }}
  li.sedang {{ border-left-color:#d97706; background:#fffbeb; }}
  li.rendah {{ border-left-color:#0284c7; background:#f0f9ff; }}
  .tlevel {{ font-weight:700; font-size:12px; letter-spacing:.04em; margin-bottom:3px; }}
  .tdesc {{ margin-bottom:3px; }}
  .tsrc {{ font-size:11px; color:var(--mut); }}
  .note {{ margin-top:22px; padding:14px 16px; border-radius:10px; background:#fff8e6;
           border:1px solid #f3d9a4; font-size:12.5px; color:#6b4e12; }}
  .note b {{ color:#4a3708; }}
  footer {{ padding:14px 28px; background:#f8fafc; border-top:1px solid var(--line);
            font-size:11px; color:var(--mut); display:flex; justify-content:space-between; }}
</style>
</head>
<body>
<div class="card">
  <header>
    <div class="eyebrow">Layar Konfirmasi SPJ &mdash; Meja Pimpinan</div>
    <h1>SPJ-2026-011</h1>
    <div class="sub">Draf untuk konfirmasi bendahara. Belum disetujui, belum siap cair.</div>
  </header>
  <div class="body">
    <div class="meta">
      <div><span>Nomor</span><span>SPJ-2026-011</span></div>
      <div><span>Pegawai</span><span>{hasil['pegawai']['nama']}</span></div>
      <div><span>NIP</span><span>{hasil['pegawai']['nip']}</span></div>
      <div><span>Golongan</span><span>{hasil['pegawai']['golongan']}</span></div>
      <div><span>Tujuan</span><span>Jakarta (DKI Jakarta)</span></div>
      <div><span>Tanggal SPT</span><span>5&ndash;7 Oktober 2026</span></div>
    </div>

    <h2>Rincian Biaya</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>Jenis</th><th>Kutipan Bukti</th><th style="text-align:right">Diajukan</th><th style="text-align:right">Dibayar</th><th>Status</th></tr>
      </thead>
      <tbody>
{rows}      </tbody>
      <tfoot>
        <tr class="total">
          <td colspan="3">TOTAL</td>
          <td class="num">{rp(hasil['total_diajukan'])}</td>
          <td class="num">{rp(hasil['total_dibayar'])}</td>
          <td></td>
        </tr>
      </tfoot>
    </table>

    <div class="totals">
      <div class="tbox">
        <div class="lbl">Total Diajukan</div>
        <div class="val">{rp(hasil['total_diajukan'])}</div>
      </div>
      <div class="tbox pay">
        <div class="lbl">Total Dibayar</div>
        <div class="val">{rp(hasil['total_dibayar'])}</div>
      </div>
    </div>

    <h2>Temuan ({len(temuan)}) &mdash; urut KRITIS &rarr; TINGGI &rarr; SEDANG</h2>
    <ul class="temuan-list">
{tlis}    </ul>

    <div class="note">
      <b>Keputusan dan pencairan berada di tangan bendahara di Meja Pimpinan.</b>
      Layar ini hanya menampilkan hasil verifikasi dan temuan apa adanya; tidak menyetujui,
      tidak menandai siap cair, dan tidak mengubah angka. Item B02 (taksi Rp 210.000) berstatus
      DITAHAN, sehingga total dibayar {rp(hasil['total_dibayar'])} dari {rp(hasil['total_diajukan'])} yang diajukan.
      Temuan KRITIS (R06) dan TINGGI (R10) wajib diputuskan sebelum persetujuan.
    </div>
  </div>
  <footer>
    <span>Sumber angka: periksa_aturan (kasus-011) &middot; auditor: eskalasi</span>
    <span>Draf &mdash; bukan dokumen persetujuan</span>
  </footer>
</div>
</body>
</html>
"""
open(os.path.join(OUT, "layar_konfirmasi.html"), "w", encoding="utf-8").write(html)

# ---------------- draf_spj.docx ----------------
doc = Document()
for s in doc.sections:
    s.top_margin = Cm(2.2); s.bottom_margin = Cm(2.2)
    s.left_margin = Cm(2.6); s.right_margin = Cm(2.2)
st = doc.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(10.5)

h = doc.add_paragraph(); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = h.add_run("DRAF SURAT PERINTAH PERJALANAN DINAS (SPJ)"); run.bold = True; run.font.size = Pt(14)
sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = sub.add_run("Nomor: SPJ-2026-011"); r2.bold = True; r2.font.size = Pt(11)
note = doc.add_paragraph(); note.alignment = WD_ALIGN_PARAGRAPH.CENTER
nr = note.add_run("Draf \u2014 belum disetujui, bukan dokumen pencairan"); nr.italic = True
nr.font.size = Pt(9); nr.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

def kv(label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    a = p.add_run(f"{label}: "); a.bold = True
    p.add_run(value)

def heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    rr = p.add_run(text); rr.bold = True; rr.font.size = Pt(11)

heading("A. Identitas Pegawai")
kv("Nama", hasil["pegawai"]["nama"])
kv("NIP", hasil["pegawai"]["nip"])
kv("Golongan", hasil["pegawai"]["golongan"])

heading("B. Maksud dan Tujuan")
kv("Maksud", "Perjalanan dinas ke Jakarta")
kv("Tujuan", "Jakarta (DKI Jakarta)")
kv("Tanggal SPT", "5-7 Oktober 2026")
kv("Lama perjalanan", f"{uh['hari']} hari")

heading("C. Rincian Biaya")
tbl = doc.add_table(rows=1, cols=5)
tbl.style = "Table Grid"
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = tbl.rows[0].cells
for i, txt in enumerate(["ID", "Jenis", "Uraian", "Diajukan", "Dibayar"]):
    hdr[i].text = ""
    pr = hdr[i].paragraphs[0].add_run(txt); pr.bold = True
    pr.font.size = Pt(9.5)

for it in hasil["items"]:
    cells = tbl.add_row().cells
    cells[0].text = it["id"]
    cells[1].text = it["jenis"]
    cells[2].text = kutipan.get(it["id"], "")
    cells[3].text = rp(it["nilai_diajukan"])
    cells[4].text = rp(it["nilai_dibayar"])

cells = tbl.add_row().cells
cells[0].text = "UH"
cells[1].text = "uang harian"
cells[2].text = f"{uh['hari']} hari x {rp(uh['tarif'])} (R04)"
cells[3].text = rp(uh["total"])
cells[4].text = rp(uh["total"])

cells = tbl.add_row().cells
cells[0].text = "TOTAL"
cells[1].text = ""
cells[2].text = ""
cells[3].text = rp(hasil["total_diajukan"])
cells[4].text = rp(hasil["total_dibayar"])
for c in cells:
    for p in c.paragraphs:
        for r_ in p.runs:
            r_.bold = True

for row in tbl.rows:
    for i, c in enumerate(row.cells):
        for p in c.paragraphs:
            p.paragraph_format.space_after = Pt(0)
            if i >= 3:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for r_ in p.runs:
                if r_.font.size is None:
                    r_.font.size = Pt(9.5)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(8)
p.add_run("Total dibayar: ").bold = True
p.add_run(rp(hasil["total_dibayar"]) + " dari " + rp(hasil["total_diajukan"]) + " yang diajukan.")

heading(f"D. Catatan Temuan ({len(temuan)})")
for i, t in enumerate(temuan, 1):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    a = p.add_run(f"[{t['level'].upper()}] {t['aturan']} \u2014 "); a.bold = True
    p.add_run(t["deskripsi"])
    p.add_run(f" (sumber: {t['sumber'] if t['sumber'] else '-'})").italic = True

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(10)
nr2 = p.add_run("Keputusan persetujuan dan pencairan berada pada bendahara di Meja Pimpinan. "
                "Dokumen ini adalah draf hasil verifikasi, bukan dokumen persetujuan atau pencairan.")
nr2.italic = True; nr2.font.size = Pt(9); nr2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

doc.save(os.path.join(OUT, "draf_spj.docx"))
print("built:", sorted(os.listdir(OUT)))
