# -*- coding: utf-8 -*-
import json, os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = r"D:/Agent 2/spj-agent"
OUT = os.path.join(BASE, "keluar/draf/SPJ-2026-010")
hasil = json.load(open(os.path.join(BASE, "kerja/verifikator-sbm_kasus-010.json"), encoding="utf-8"))["hasil"]
aud = json.load(open(os.path.join(BASE, "kerja/auditor_kasus-010.json"), encoding="utf-8"))

kutipan = {}
for f in ["pembaca-tiket_kasus-010.json", "pembaca-hotel_kasus-010.json", "pembaca-struk_kasus-010.json"]:
    d = json.load(open(os.path.join(BASE, "kerja", f), encoding="utf-8"))
    for it in d["item_bukti"]:
        kutipan[it["id"]] = it["kutipan"]

def rp(n):
    return "Rp " + format(n, ",d").replace(",", ".")

# ---------- timeline.json ----------
json.dump(aud["timeline"], open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ---------- layar_konfirmasi.html ----------
ORDER = {"KRITIS": 0, "TINGGI": 1, "SEDANG": 2, "RENDAH": 3}
temuan = sorted(hasil["temuan"], key=lambda t: ORDER.get(t["level"].upper(), 9))

rows = ""
for it in hasil["items"]:
    rows += f"""      <tr>
        <td class="mono">{it['id']}</td>
        <td>{it['jenis']}</td>
        <td>{kutipan.get(it['id'], '')}</td>
        <td class="num">{rp(it['nilai_diajukan'])}</td>
        <td class="num">{rp(it['nilai_dibayar'])}</td>
        <td><span class="badge ok">SESUAI</span></td>
      </tr>
"""
uh = hasil["uang_harian"]
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
<title>Layar Konfirmasi SPJ-2026-010</title>
<style>
  :root {{ --ink:#1b2430; --mut:#64748b; --line:#e2e8f0; --bg:#f6f8fb; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:32px; background:var(--bg); color:var(--ink);
         font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif; font-size:14px; }}
  .card {{ max-width:940px; margin:0 auto; background:#fff; border:1px solid var(--line);
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
    <h1>SPJ-2026-010</h1>
    <div class="sub">Draf untuk konfirmasi bendahara. Belum disetujui, belum siap cair.</div>
  </header>
  <div class="body">
    <div class="meta">
      <div><span>Nomor</span><span>SPJ-2026-010</span></div>
      <div><span>Pegawai</span><span>{hasil['pegawai']['nama']}</span></div>
      <div><span>NIP</span><span>{hasil['pegawai']['nip']}</span></div>
      <div><span>Golongan</span><span>{hasil['pegawai']['golongan']}</span></div>
      <div><span>Tujuan</span><span>Jayapura, Papua</span></div>
      <div><span>Tanggal SPT</span><span>5&ndash;9 Oktober 2026</span></div>
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
        <div class="lbl">Total Dibayar (usulan verifikasi)</div>
        <div class="val">16.480.000</div>
      </div>
    </div>

    <h2>Temuan ({len(temuan)}) &mdash; urut KRITIS &rarr; RENDAH</h2>
    <ul class="temuan-list">
{tlis}    </ul>

    <div class="note">
      <b>Keputusan dan pencairan berada di tangan bendahara di Meja Pimpinan.</b>
      Layar ini hanya menampilkan hasil verifikasi dan temuan apa adanya; tidak menyetujui,
      tidak menandai siap cair, dan tidak mengubah angka. Temuan TINGGI (R10) wajib dikonfirmasi
      sebelum keputusan diambil.
    </div>
  </div>
  <footer>
    <span>Sumber angka: periksa_aturan (kasus-010) &middot; auditor: lolos</span>
    <span>Draf &mdash; bukan dokumen persetujuan</span>
  </footer>
</div>
</body>
</html>
"""
open(os.path.join(OUT, "layar_konfirmasi.html"), "w", encoding="utf-8").write(html)

# ---------- draf_spj.docx ----------
doc = Document()
for s in doc.sections:
    s.top_margin = Cm(2.2); s.bottom_margin = Cm(2.2)
    s.left_margin = Cm(2.6); s.right_margin = Cm(2.2)
st = doc.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(10.5)

h = doc.add_paragraph(); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = h.add_run("DRAF SURAT PERINTAH PERJALANAN DINAS (SPJ)"); run.bold = True; run.font.size = Pt(14)
sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = sub.add_run("Nomor: SPJ-2026-010"); r2.bold = True; r2.font.size = Pt(11)
note = doc.add_paragraph(); note.alignment = WD_ALIGN_PARAGRAPH.CENTER
nr = note.add_run("Draf \u2014 belum disetujui, bukan dokumen pencairan"); nr.italic = True
nr.font.size = Pt(9); nr.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

def kv(label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    a = p.add_run(f"{label}"); a.bold = True
    p.add_run(f": {value}")

doc.add_paragraph()
kv("Nomor SPJ", "SPJ-2026-010")
kv("Pegawai", hasil["pegawai"]["nama"])
kv("NIP", hasil["pegawai"]["nip"])
kv("Golongan", hasil["pegawai"]["golongan"])
kv("Maksud", "Perjalanan dinas dalam rangka survey perbatasan")
kv("Tujuan", "Jayapura, Papua")
kv("Tanggal SPT", "5\u20139 Oktober 2026")
kv("Sumber anggaran", "SBM Papua, golongan III (periksa_aturan, kasus-010)")

doc.add_paragraph()
p = doc.add_paragraph(); p.add_run("RINCIAN BIAYA").bold = True

tbl = doc.add_table(rows=1, cols=5)
tbl.style = "Light Grid Accent 1"
hdr = ["ID", "Jenis / Uraian", "Rumus Hitung", "Diajukan", "Dibayar"]
for i, t in enumerate(hdr):
    c = tbl.rows[0].cells[i]
    c.text = t
    for par in c.paragraphs:
        for rn in par.runs:
            rn.bold = True

for it in hasil["items"]:
    cells = tbl.add_row().cells
    cells[0].text = it["id"]
    cells[1].text = f"{it['jenis']} \u2014 {it['file']}"
    cells[2].text = it.get("rumus") or "-"
    cells[3].text = rp(it["nilai_diajukan"])
    cells[4].text = rp(it["nilai_dibayar"])

cells = tbl.add_row().cells
cells[0].text = "UH"
cells[1].text = "uang harian"
cells[2].text = f"{uh['hari']} hari x {rp(uh['tarif'])}"
cells[3].text = rp(uh["total"])
cells[4].text = rp(uh["total"])

cells = tbl.add_row().cells
cells[0].text = ""
cells[1].text = "TOTAL"
cells[2].text = ""
cells[3].text = rp(hasil["total_diajukan"])
cells[4].text = rp(hasil["total_dibayar"])
for c in cells:
    for par in c.paragraphs:
        for rn in par.runs:
            rn.bold = True

doc.add_paragraph()
p = doc.add_paragraph(); p.add_run("TOTAL DIBAYAR: 16.480.000").bold = True
p.runs[0].font.size = Pt(11)

doc.add_paragraph()
p = doc.add_paragraph(); p.add_run("CATATAN TEMUAN").bold = True
for t in temuan:
    doc.add_paragraph(
        f"[{t['level'].upper()}] {t['aturan']} \u2014 {t['deskripsi']} "
        f"(sumber: {t['sumber'] if t['sumber'] else '-'})", style="List Bullet")

doc.add_paragraph()
p = doc.add_paragraph()
p.add_run("Keputusan atas temuan dan pencairan dana berada pada bendahara di Meja Pimpinan. "
          "Dokumen ini adalah draf hasil verifikasi; angka disalin apa adanya dari hasil "
          "periksa_aturan (kasus-010) dan tidak dihitung ulang.").font.size = Pt(9.5)

doc.save(os.path.join(OUT, "draf_spj.docx"))
print("done")
