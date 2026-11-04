import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE = r"D:/Agent 2/spj-agent"
OUT = os.path.join(BASE, "keluar/draf/SPJ-2026-010")

hasil = json.load(open(os.path.join(BASE, "kerja/verifikator-sbm_kasus-010.json"), encoding="utf-8"))["hasil"]
aud = json.load(open(os.path.join(BASE, "kerja/auditor_kasus-010.json"), encoding="utf-8"))

kutipan = {}
yakin = {}
for f in ["pembaca-tiket_kasus-010.json", "pembaca-hotel_kasus-010.json", "pembaca-struk_kasus-010.json"]:
    d = json.load(open(os.path.join(BASE, "kerja", f), encoding="utf-8"))
    for it in d["item_bukti"]:
        kutipan[it["id"]] = it["kutipan"]
        yakin[it["id"]] = it["yakin"]

# ---------- rekap.xlsx ----------
wb = Workbook()
ws = wb.active
ws.title = "rekap"
headers = ["id_bukti", "jenis", "file_sumber", "kutipan_teks", "kode_aturan", "rumus_hitung",
           "nilai_diajukan", "nilai_dibayar", "selisih", "yakin_pembaca", "level_risiko", "status"]
ws.append(headers)

r = 2
for it in hasil["items"]:
    ws.append([it["id"], it["jenis"], it["file"], kutipan.get(it["id"], ""), "-", it.get("rumus") or "-",
               it["nilai_diajukan"], it["nilai_dibayar"], f"=G{r}-H{r}",
               yakin.get(it["id"], "-"), "-", "sesuai"])
    r += 1

uh = hasil["uang_harian"]
ws.append(["uang_harian", "uang_harian", "SBM Papua III (periksa_aturan)",
           f"Uang harian {uh['hari']} hari x Rp {uh['tarif']:,}".replace(",", "."),
           "R04", f"{uh['hari']} hari x Rp{uh['tarif']}", uh["total"], uh["total"],
           f"=G{r}-H{r}", "-", "-", "sesuai"])
last_data = r
r += 1

ws.append(["TOTAL", None, None, None, None, None,
           f"=SUM(G2:G{last_data})", f"=SUM(H2:H{last_data})", f"=SUM(I2:I{last_data})",
           None, "TINGGI", "perlu_cek_manusia"])
total_row = r
r += 2
ws.cell(row=r, column=1, value=("Catatan: 1 temuan TINGGI (R10) - wajib konfirmasi tambahan bendahara: "
                                "total Rp16.480.000 di atas Rp10.000.000. Keputusan & pencairan oleh bendahara "
                                "di Meja Pimpinan."))

# styling
hdr_fill = PatternFill("solid", fgColor="1F3864")
thin = Side(style="thin", color="D9D9D9")
for c in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=c)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = hdr_fill
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for row in ws.iter_rows(min_row=2, max_row=total_row, max_col=len(headers)):
    for cell in row:
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        if cell.column in (7, 8, 9):
            cell.number_format = '#,##0'
for c in range(1, len(headers) + 1):
    ws.cell(row=total_row, column=c).font = Font(bold=True)
    ws.cell(row=total_row, column=c).fill = PatternFill("solid", fgColor="F1F5FB")
widths = [12, 12, 22, 62, 12, 40, 15, 15, 12, 14, 13, 18]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:L{total_row - 1}"
wb.save(os.path.join(OUT, "rekap.xlsx"))

# ---------- verifikasi SUM ----------
wb2 = __import__("openpyxl").load_workbook(os.path.join(OUT, "rekap.xlsx"))
ws2 = wb2.active
s = sum(ws2.cell(row=i, column=8).value for i in range(2, last_data + 1))
print("SUM nilai_dibayar =", s)
print("total_dibayar tool =", hasil["total_dibayar"])
print("MATCH:", s == hasil["total_dibayar"] == 16480000)
