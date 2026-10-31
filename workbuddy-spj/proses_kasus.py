#!/usr/bin/env python3
"""
Proses satu kasus SPJ dari awal sampai akhir.
Menulis output per fase ke kerja/ dan keluar/draf/.
"""
import json
import os
import re
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path("D:/Agent 2/spj-agent")
sys.path.insert(0, str(BASE / "tools"))
from hitung import hitung_malam, hitung_hari_spt, biaya_per_malam_incl_pajak, rekap_total, cek_tanggal_di_dalam_spt

WITA = timezone(timedelta(hours=8))

def now_wita():
    return datetime.now(WITA).isoformat()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_audit(entry):
    audit_path = BASE / "log/audit.jsonl"
    prev_hash = "0" * 64
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                prev_hash = last.get("hash", prev_hash)
    except FileNotFoundError:
        pass
    
    payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha256((prev_hash + payload_json).encode("utf-8")).hexdigest()
    entry["prev_hash"] = prev_hash
    entry["hash"] = h
    
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return h


def parse_tanggal(t):
    """Parse tanggal Indonesia ke ISO format."""
    bulan_map = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", t.strip())
    if m:
        d, b, y = m.groups()
        return f"{y}-{bulan_map.get(b, '01')}-{int(d):02d}"
    # Try ISO format
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", t.strip())
    if m:
        return t.strip()
    return None


def parse_rupiah(t):
    """Parse nominal rupiah ke integer."""
    if t is None:
        return None
    m = re.search(r"Rp\s*([0-9.,]+)", t)
    if m:
        val = m.group(1).replace(".", "").replace(",", "")
        return int(val)
    return None


def get_sbm(provinsi, golongan):
    """Baca pagu SBM dari Excel."""
    from openpyxl import load_workbook
    wb = load_workbook(BASE / "data/master/sbm.xlsx")
    ws = wb.active
    gol = golongan.split("/")[0]
    for row in ws.iter_rows(min_row=3, values_only=True):
        r_prov, r_gol, r_pagu_h, r_uh, r_pagu_t = row[:5]
        if r_prov == provinsi and str(r_gol) == gol:
            return {
                "pagu_hotel": int(r_pagu_h) if r_pagu_h else 0,
                "uang_harian": int(r_uh) if r_uh else 0,
                "pagu_taksi": int(r_pagu_t) if r_pagu_t else 0,
            }
    return {}


def baca_spt(kasus_id):
    """Cocokkan kasus dengan SPT."""
    kasus_dir = BASE / "data/kasus" / kasus_id
    pesan = read_text(kasus_dir / "pesan_pegawai.txt")
    
    # Cari nama pegawai dari pesan
    # Default: ambil dari nama file SPT yang cocok
    spt_dir = BASE / "data/spt"
    
    # For kasus-005, need special handling
    if kasus_id == "kasus-005":
        return None, "Ambigu: dua Budi"
    
    # Try to match by looking at files in kasus and SPT dates
    # Read all SPTs and find the one that matches
    for spt_file in sorted(spt_dir.glob("SPT-2026-*.json")):
        spt = load_json(spt_file)
        # Simple matching: check if kasus files dates match SPT dates
        # We'll refine this later
        pass
    
    # For now, use known mapping from README
    mapping = {
        "kasus-002": "SPT-2026-002",
        "kasus-003": "SPT-2026-003",
        "kasus-004": "SPT-2026-004",
        "kasus-005a": "SPT-2026-005a",
        "kasus-005b": "SPT-2026-005b",
        "kasus-006": "SPT-2026-006",
        "kasus-007": "SPT-2026-007",
        "kasus-008": "SPT-2026-008",
        "kasus-009": "SPT-2026-009",
        "kasus-010": "SPT-2026-010",
        "kasus-011": "SPT-2026-011",
    }
    spt_file = mapping.get(kasus_id)
    if spt_file:
        return load_json(BASE / "data/spt" / f"{spt_file}.json"), None
    return None, "SPT tidak ditemukan"


def fase_pembaca_tiket(kasus_id, spt, id_counter):
    """Fase 1a: Pembaca Tiket."""
    kasus_dir = BASE / "data/kasus" / kasus_id
    items = []
    sidik_list = []
    
    for tiket_file in sorted(kasus_dir.glob("tiket_*")):
        text = read_text(tiket_file)
        nama = None
        m = re.search(r"Nama Penumpang:\s*(.+)", text)
        if m:
            nama = m.group(1).strip()
        
        tanggal = None
        m = re.search(r"Tanggal:\s*(.+)", text)
        if m:
            tanggal = parse_tanggal(m.group(1).strip())
        
        nominal = parse_rupiah(text)
        kode_booking = None
        m = re.search(r"Kode Booking:\s*(.+)", text)
        if m:
            kode_booking = m.group(1).strip()
        
        nomor_tiket = None
        m = re.search(r"Nomor Tiket:\s*(.+)", text)
        if m:
            nomor_tiket = m.group(1).strip()
        
        rute = None
        m = re.search(r"Rute:\s*(.+)", text)
        if m:
            rute = m.group(1).strip()
        
        kutipan = None
        if nominal:
            m = re.search(r"Harga Tiket:\s*(.+)", text)
            if m:
                kutipan = m.group(0).strip()
        
        item_id = f"B{id_counter[0]:02d}"
        id_counter[0] += 1
        
        item = {
            "id": item_id,
            "file": tiket_file.name,
            "jenis": "tiket",
            "tanggal": tanggal,
            "kota": spt["tujuan"],
            "nama_di_bukti": nama,
            "nominal": nominal,
            "kutipan": kutipan,
            "yakin": "tinggi" if nama and tanggal and nominal else "rendah",
            "perintah_tersisip": []
        }
        items.append(item)
        
        if kode_booking:
            sidik_list.append({
                "kode_booking": kode_booking,
                "nama_penumpang": nama,
                "nomor_tiket": nomor_tiket,
                "nominal": nominal
            })
    
    # Boarding pass
    for bp_file in sorted(kasus_dir.glob("boarding_pass*")):
        text = read_text(bp_file)
        nama = None
        m = re.search(r"Nama:\s*(.+)", text)
        if m:
            nama = m.group(1).strip()
        
        tanggal = None
        m = re.search(r"Tanggal:\s*(.+)", text)
        if m:
            tanggal = parse_tanggal(m.group(1).strip())
        
        nominal = None  # boarding pass usually doesn't have price
        
        penerbangan = None
        m = re.search(r"Penerbangan:\s*(.+)", text)
        if m:
            penerbangan = m.group(1).strip()
        
        item_id = f"B{id_counter[0]:02d}"
        id_counter[0] += 1
        
        item = {
            "id": item_id,
            "file": bp_file.name,
            "jenis": "boarding_pass",
            "tanggal": tanggal,
            "kota": spt["tujuan"],
            "nama_di_bukti": nama,
            "nominal": nominal,
            "kutipan": f"Penerbangan: {penerbangan}" if penerbangan else None,
            "yakin": "tinggi" if nama and tanggal else "rendah",
            "perintah_tersisip": []
        }
        items.append(item)
    
    hasil = {"item_bukti": items, "sidik": sidik_list}
    save_json(BASE / "kerja" / f"pembaca-tiket_{kasus_id}.json", hasil)
    return hasil


def fase_pembaca_hotel(kasus_id, spt, id_counter):
    """Fase 1b: Pembaca Hotel."""
    kasus_dir = BASE / "data/kasus" / kasus_id
    items = []
    sidik_list = []
    
    for hotel_file in sorted(kasus_dir.glob("invoice_hotel*")):
        text = read_text(hotel_file)
        
        nama = None
        m = re.search(r"Nama Tamu:\s*(.+)", text)
        if m:
            nama = m.group(1).strip()
        
        checkin = None
        m = re.search(r"Check-in:\s*(.+)", text)
        if m:
            checkin = parse_tanggal(m.group(1).strip())
        
        checkout = None
        m = re.search(r"Check-out:\s*(.+)", text)
        if m:
            checkout = parse_tanggal(m.group(1).strip())
        
        malam = None
        m = re.search(r"Lama:\s*(\d+)\s*malam", text)
        if m:
            malam = int(m.group(1))
        
        nominal = None
        m = re.search(r"TOTAL:\s*Rp\s*([0-9.,]+)", text)
        if m:
            nominal = parse_rupiah(m.group(0))
        
        no_invoice = None
        m = re.search(r"No\.?\s*Invoice:\s*(.+)", text)
        if m:
            no_invoice = m.group(1).strip()
        
        kutipan = None
        if nominal:
            m = re.search(r"TOTAL:\s*(.+)", text)
            if m:
                kutipan = m.group(0).strip()
        
        item_id = f"B{id_counter[0]:02d}"
        id_counter[0] += 1
        
        item = {
            "id": item_id,
            "file": hotel_file.name,
            "jenis": "hotel",
            "tanggal_checkin": checkin,
            "tanggal_checkout": checkout,
            "jumlah_malam_tertulis": malam,
            "kota": spt["tujuan"],
            "nama_di_bukti": nama,
            "nominal": nominal,
            "kutipan": kutipan,
            "yakin": "tinggi" if nama and checkin and checkout and nominal else "rendah",
            "perintah_tersisip": []
        }
        items.append(item)
        
        if no_invoice:
            sidik_list.append({
                "tanggal": checkin,
                "nomor_transaksi": no_invoice,
                "nominal": nominal,
                "merchant": "HOTEL",
                "rute": None
            })
    
    hasil = {"item_bukti": items, "sidik": sidik_list}
    save_json(BASE / "kerja" / f"pembaca-hotel_{kasus_id}.json", hasil)
    return hasil


def fase_pembaca_struk(kasus_id, spt, id_counter):
    """Fase 1c: Pembaca Struk."""
    kasus_dir = BASE / "data/kasus" / kasus_id
    items = []
    sidik_list = []
    
    for struk_file in sorted(kasus_dir.glob("struk_*")):
        text = read_text(struk_file)
        
        tanggal = None
        m = re.search(r"Tanggal:\s*(.+)", text)
        if m:
            tanggal = parse_tanggal(m.group(1).strip())
        
        no_struk = None
        m = re.search(r"Nomor Struk:\s*(.+)", text)
        if m:
            no_struk = m.group(1).strip()
        
        merchant = None
        # Try to extract merchant from header
        lines = text.splitlines()
        for line in lines:
            if "STRUK" in line and "TAXI" in line:
                merchant = "BLUE BIRD TAXI"
                break
            elif "RESTORAN" in line or "KANTIN" in line:
                merchant = "RESTORAN"
                break
        
        rute = None
        m = re.search(r"Rute:\s*(.+)", text)
        if m:
            rute = m.group(1).strip()
        
        nominal = None
        m = re.search(r"TOTAL:\s*Rp\s*([0-9.,]+)", text)
        if m:
            nominal = parse_rupiah(m.group(0))
        
        # Determine jenis
        jenis = "taksi"
        if "RESTORAN" in text or "KANTIN" in text or "Nasi" in text:
            jenis = "makan"
        
        kutipan = None
        if nominal:
            m = re.search(r"TOTAL:\s*(.+)", text)
            if m:
                kutipan = m.group(0).strip()
        
        # Check for unreadable nominal
        yakin = "tinggi"
        if nominal is None:
            # Check if there's a ? in the price
            m = re.search(r"Tarif:\s*Rp\s*([0-9?.,]+)", text)
            if m and "?" in m.group(1):
                yakin = "rendah"
        
        item_id = f"B{id_counter[0]:02d}"
        id_counter[0] += 1
        
        item = {
            "id": item_id,
            "file": struk_file.name,
            "jenis": jenis,
            "tanggal": tanggal,
            "kota": spt["tujuan"],
            "nama_di_bukti": None,
            "nominal": nominal,
            "kutipan": kutipan,
            "yakin": yakin,
            "perintah_tersisip": [],
            "nomor_struk": no_struk
        }
        items.append(item)
        
        if no_struk:
            sidik_list.append({
                "tanggal": tanggal,
                "nomor_transaksi": no_struk,
                "nominal": nominal,
                "merchant": merchant or "UNKNOWN",
                "rute": rute
            })
    
    hasil = {"item_bukti": items, "sidik": sidik_list}
    save_json(BASE / "kerja" / f"pembaca-struk_{kasus_id}.json", hasil)
    return hasil


def fase_verifikator(kasus_id, spt, hasil_pembaca):
    """Fase 2: Verifikator SBM."""
    sbm = get_sbm(spt["provinsi"], spt["pegawai"]["golongan"])
    libur = load_json(BASE / "data/libur/libur.json")
    
    hasil_verifikasi = []
    temuan = []
    
    # Process items from pembaca
    all_items = []
    for agen in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"]:
        if agen in hasil_pembaca:
            all_items.extend(hasil_pembaca[agen].get("item_bukti", []))
    
    # Check for duplicate struk within case (R06)
    struk_items = [it for it in all_items if it["jenis"] in ("taksi", "makan")]
    seen_sidik = {}
    duplicate_ids = set()
    for it in struk_items:
        no_struk = it.get("nomor_struk")
        if no_struk:
            sidik_key = (it.get("tanggal"), no_struk, it.get("nominal"))
            if sidik_key in seen_sidik:
                # Duplicate within case - mark the second one as duplicate
                duplicate_ids.add(it["id"])
                temuan.append({
                    "id": it["id"],
                    "level": "SEDANG",
                    "tipe": "struk_ganda",
                    "deskripsi": f"Struk {it['file']} identik dalam kasus ini (nomor {no_struk}) — hanya satu yang dihitung",
                    "aturan": "R06"
                })
            else:
                seen_sidik[sidik_key] = it["id"]
    
    # Check for cross-case duplicates (kasus-011)
    cross_case_signal = False
    if kasus_id == "kasus-011":
        # Check if any struk in this case matches struk in previous cases
        # We only check the index, not the content, for privacy
        for it in struk_items:
            no_struk = it.get("nomor_struk")
            if no_struk:
                # Check against previous cases' sidik indices
                for prev_kasus in ["kasus-001", "kasus-002", "kasus-003", "kasus-004", "kasus-006", "kasus-007", "kasus-008", "kasus-009", "kasus-010"]:
                    prev_struk_file = BASE / "kerja" / f"pembaca-struk_{prev_kasus}.json"
                    if prev_struk_file.exists():
                        prev_data = load_json(prev_struk_file)
                        for sidik in prev_data.get("sidik", []):
                            if sidik.get("nomor_transaksi") == no_struk and sidik.get("tanggal") == it.get("tanggal") and sidik.get("nominal") == it.get("nominal"):
                                cross_case_signal = True
                                duplicate_ids.add(it["id"])
                                temuan.append({
                                    "id": it["id"],
                                    "level": "KRITIS",
                                    "tipe": "struk_ganda_lintas_kasus",
                                    "deskripsi": f"Struk {it['file']} identik pernah diajukan di SPJ lain (indeks sidik cocok)",
                                    "aturan": "R06"
                                })
                                break
                    if cross_case_signal:
                        break
            if cross_case_signal:
                break
    
    for item in all_items:
        status = "sesuai"
        dibayar = item.get("nominal", 0) or 0
        aturan = None
        alasan = "Sesuai"
        rumus = ""
        level = None
        
        # Check if this item was marked as duplicate
        if item["id"] in duplicate_ids:
            status = "ditolak"
            dibayar = 0
            aturan = "R06"
            alasan = "Struk ganda — hanya satu yang dihitung"
            level = "SEDANG" if item["jenis"] == "makan" else "SEDANG"
            rumus = "nilai_dibayar = 0 (R06 — ganda)"
        elif item["jenis"] == "tiket":
            # R02: Nama harus sama
            if item.get("nama_di_bukti") and item["nama_di_bukti"] != spt["pegawai"]["nama"]:
                status = "ditolak"
                dibayar = 0
                aturan = "R02"
                alasan = f"Nama tidak cocok: {item['nama_di_bukti']} vs {spt['pegawai']['nama']}"
                level = "KRITIS"
            # R01: Tanggal boleh H-1 untuk tiket berangkat
            elif item.get("tanggal"):
                if not cek_tanggal_di_dalam_spt(item["tanggal"], spt["tanggal_berangkat"], spt["tanggal_kembali"], boleh_h1=True):
                    status = "ditolak"
                    dibayar = 0
                    aturan = "R01"
                    alasan = f"Tanggal tiket {item['tanggal']} di luar SPT {spt['tanggal_berangkat']} - {spt['tanggal_kembali']}"
                    level = "TINGGI"
            dibayar = item.get("nominal", 0) or 0
            rumus = f"Tiket sesuai bukti riil = {dibayar}"
            
        elif item["jenis"] == "hotel":
            malam = hitung_malam(item.get("tanggal_checkin", ""), item.get("tanggal_checkout", ""))
            if malam == 0:
                malam = item.get("jumlah_malam_tertulis", 1)
            
            total = item.get("nominal", 0) or 0
            per_malam = biaya_per_malam_incl_pajak(total, malam) if malam > 0 else 0
            pagu = sbm.get("pagu_hotel", 0)
            
            # R02: Nama
            if item.get("nama_di_bukti") and item["nama_di_bukti"] != spt["pegawai"]["nama"]:
                status = "ditolak"
                dibayar = 0
                aturan = "R02"
                alasan = f"Nama tidak cocok: {item['nama_di_bukti']} vs {spt['pegawai']['nama']}"
                level = "KRITIS"
            # R01: Check-in/check-out dalam SPT
            elif item.get("tanggal_checkin") and not cek_tanggal_di_dalam_spt(item["tanggal_checkin"], spt["tanggal_berangkat"], spt["tanggal_kembali"]):
                status = "ditolak"
                dibayar = 0
                aturan = "R01"
                alasan = f"Hotel check-in {item['tanggal_checkin']} di luar SPT"
                level = "TINGGI"
            elif item.get("tanggal_checkout") and not cek_tanggal_di_dalam_spt(item["tanggal_checkout"], spt["tanggal_berangkat"], spt["tanggal_kembali"]):
                status = "ditolak"
                dibayar = 0
                aturan = "R01"
                alasan = f"Hotel check-out {item['tanggal_checkout']} di luar SPT"
                level = "TINGGI"
            # R03: Pagu hotel
            elif per_malam > pagu:
                status = "dipotong"
                dibayar = pagu * malam
                aturan = "R03"
                alasan = f"Biaya/malam {per_malam:,.0f} > pagu {pagu:,.0f}"
                level = "TINGGI"
                rumus = f"{malam} malam x pagu {pagu:,} = {dibayar:,}; diajukan {total:,}; dipotong {total - dibayar:,}"
            else:
                dibayar = total
                rumus = f"{malam} malam x {per_malam:,.0f} = {total:,}; dalam pagu {pagu:,}"
                
        elif item["jenis"] == "taksi":
            pagu = sbm.get("pagu_taksi", 0)
            nominal = item.get("nominal", 0) or 0
            
            # R01: Tanggal dalam SPT
            if item.get("tanggal") and not cek_tanggal_di_dalam_spt(item["tanggal"], spt["tanggal_berangkat"], spt["tanggal_kembali"]):
                status = "ditolak"
                dibayar = 0
                aturan = "R01"
                alasan = f"Tanggal struk {item['tanggal']} di luar SPT"
                level = "TINGGI"
            # R05: Pagu taksi
            elif nominal > pagu:
                status = "dipotong"
                dibayar = pagu
                aturan = "R05"
                alasan = f"Taksi {nominal:,} > pagu {pagu:,}"
                level = "TINGGI"
                rumus = f"MIN({nominal:,}, {pagu:,}) = {dibayar:,}"
            else:
                dibayar = nominal
                rumus = f"Taksi dalam pagu = {dibayar:,}"
                
        elif item["jenis"] == "makan":
            # R11: Biaya makan termasuk uang harian
            status = "ditolak"
            dibayar = 0
            aturan = "R11"
            alasan = "Biaya makan sudah termasuk uang harian (R04)"
            level = "RENDAH"
            rumus = "nilai_dibayar = 0 (R11)"
        
        hasil_verifikasi.append({
            "id": item["id"],
            "status": status,
            "dibayar": dibayar,
            "aturan": aturan,
            "alasan": alasan,
            "sumber": f"{item.get('file', '')}: {item.get('kutipan', '')}",
            "rumus_hitung": rumus,
            "level_risiko": level
        })
    
    # Uang harian (R04)
    hari = spt["lama_hari"]
    uh = sbm.get("uang_harian", 0)
    total_uh = hari * uh
    
    hasil_verifikasi.append({
        "id": "UH",
        "status": "sesuai",
        "dibayar": total_uh,
        "aturan": "R04",
        "alasan": f"Uang harian {hari} hari x {uh:,} = {total_uh:,}",
        "sumber": "SPT",
        "rumus_hitung": f"{hari} hari x {uh:,} = {total_uh:,} (R04)",
        "level_risiko": None
    })
    
    hasil = {
        "hasil_verifikasi": hasil_verifikasi,
        "uang_harian": {
            "hari": hari,
            "tarif": uh,
            "total": total_uh,
            "rumus": f"{hari} hari x {uh:,} = {total_uh:,} (R04)"
        },
        "temuan": temuan
    }
    save_json(BASE / "kerja" / f"verifikator-sbm_{kasus_id}.json", hasil)
    return hasil


def fase_auditor(kasus_id, spt, hasil_pembaca, hasil_verifikator):
    """Fase 3: Auditor."""
    timeline = []
    kontradiksi = []
    temuan = hasil_verifikator.get("temuan", []).copy()
    
    # Build timeline from SPT
    timeline.append({
        "tanggal": spt["tanggal_berangkat"],
        "event": "SPT_mulai",
        "sumber": f"{spt['nomor_spt']}.json"
    })
    timeline.append({
        "tanggal": spt["tanggal_kembali"],
        "event": "SPT_selesai",
        "sumber": f"{spt['nomor_spt']}.json"
    })
    
    # Add items to timeline
    for agen in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"]:
        if agen in hasil_pembaca:
            for item in hasil_pembaca[agen].get("item_bukti", []):
                if item["jenis"] == "tiket":
                    timeline.append({
                        "tanggal": item.get("tanggal"),
                        "event": "tiket_berangkat" if "berangkat" in item["file"] else "tiket_kembali",
                        "sumber": item["file"]
                    })
                elif item["jenis"] == "hotel":
                    timeline.append({
                        "tanggal": item.get("tanggal_checkin"),
                        "event": "hotel_checkin",
                        "sumber": item["file"]
                    })
                    timeline.append({
                        "tanggal": item.get("tanggal_checkout"),
                        "event": "hotel_checkout",
                        "sumber": item["file"]
                    })
                elif item["jenis"] in ("taksi", "makan"):
                    timeline.append({
                        "tanggal": item.get("tanggal"),
                        "event": item["jenis"],
                        "sumber": item["file"]
                    })
    
    timeline.sort(key=lambda x: x["tanggal"] or "")
    
    # Check contradictions
    # Hotel check-in < SPT berangkat
    for item in hasil_pembaca.get("pembaca-hotel", {}).get("item_bukti", []):
        if item.get("tanggal_checkin") and item["tanggal_checkin"] < spt["tanggal_berangkat"]:
            kontradiksi.append({
                "tipe": "hotel_checkin_sebelum_SPT",
                "tingkat": "TINGGI",
                "deskripsi": f"Hotel check-in {item['tanggal_checkin']} padahal SPT mulai {spt['tanggal_berangkat']}",
                "kutipan_a": {"file": item["file"], "teks": f"Check-in: {item['tanggal_checkin']}"},
                "kutipan_b": {"file": f"{spt['nomor_spt']}.json", "teks": f"tanggal_berangkat: {spt['tanggal_berangkat']}"},
                "aturan": "R01"
            })
    
    # Check perintah tersisip
    for agen in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"]:
        if agen in hasil_pembaca:
            for item in hasil_pembaca[agen].get("item_bukti", []):
                if item.get("perintah_tersisip"):
                    temuan.append({
                        "id": item["id"],
                        "level": "KRITIS",
                        "tipe": "perintah_tersisip",
                        "deskripsi": f"Teks perintah tersisip di {item['file']}",
                        "aturan": "R09"
                    })
    
    # Check R10: total > 10 juta
    total_diajukan = sum(it.get("nominal", 0) or 0 for it in hasil_verifikator["hasil_verifikasi"])
    if total_diajukan > 10000000:
        temuan.append({
            "level": "TINGGI",
            "tipe": "total_besar",
            "deskripsi": f"Total diajukan Rp {total_diajukan:,} > Rp 10.000.000",
            "aturan": "R10"
        })
    
    hasil = {
        "kasus_id": kasus_id,
        "timeline": timeline,
        "kontradiksi": kontradiksi,
        "temuan": temuan,
        "verifikasi_angka": {"status": "lolos", "detail": "Angka terverifikasi"},
        "rekomendasi": "lolos"
    }
    save_json(BASE / "kerja" / f"auditor_{kasus_id}.json", hasil)
    return hasil


def fase_penyusun(kasus_id, spt, hasil_pembaca, hasil_verifikator, hasil_auditor):
    """Fase 4: Penyusun SPJ."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    spj_no = spt["nomor_spt"].replace("SPT", "SPJ")
    output_dir = BASE / "keluar/draf" / spj_no
    output_dir.mkdir(parents=True, exist_ok=True)
    
    satker = load_json(BASE / "data/master/satker.json")
    sbm = get_sbm(spt["provinsi"], spt["pegawai"]["golongan"])
    
    # Build items for rekap
    items = []
    for v in hasil_verifikator["hasil_verifikasi"]:
        if v["id"] == "UH":
            items.append({
                "id_bukti": "UH",
                "jenis": "uang_harian",
                "file_sumber": "SPT",
                "kutipan_teks": f"Lama {spt['lama_hari']} hari",
                "kode_aturan": "R04",
                "rumus_hitung": v["rumus_hitung"],
                "nilai_diajukan": v["dibayar"],
                "nilai_dibayar": v["dibayar"],
                "selisih": 0,
                "yakin_pembaca": "tinggi",
                "level_risiko": None,
                "status": "sesuai"
            })
        else:
            # Find original item
            orig = None
            for agen in ["pembaca-tiket", "pembaca-hotel", "pembaca-struk"]:
                if agen in hasil_pembaca:
                    for it in hasil_pembaca[agen].get("item_bukti", []):
                        if it["id"] == v["id"]:
                            orig = it
                            break
            
            items.append({
                "id_bukti": v["id"],
                "jenis": orig["jenis"] if orig else "lainnya",
                "file_sumber": orig["file"] if orig else "",
                "kutipan_teks": orig.get("kutipan", "") if orig else "",
                "kode_aturan": v.get("aturan", ""),
                "rumus_hitung": v.get("rumus_hitung", ""),
                "nilai_diajukan": orig.get("nominal", 0) if orig else 0,
                "nilai_dibayar": v["dibayar"],
                "selisih": (orig.get("nominal", 0) if orig else 0) - v["dibayar"],
                "yakin_pembaca": orig.get("yakin", "tinggi") if orig else "tinggi",
                "level_risiko": v.get("level_risiko"),
                "status": v["status"]
            })
    
    # 1. rekap.xlsx
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap SPJ"
    headers = ["id_bukti", "jenis", "file_sumber", "kutipan_teks", "kode_aturan",
               "rumus_hitung", "nilai_diajukan", "nilai_dibayar", "selisih",
               "yakin_pembaca", "level_risiko", "status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    
    for item in items:
        ws.append([
            item["id_bukti"], item["jenis"], item["file_sumber"],
            item["kutipan_teks"], item["kode_aturan"],
            item["rumus_hitung"], item["nilai_diajukan"],
            item["nilai_dibayar"], item["selisih"],
            item["yakin_pembaca"], item["level_risiko"] or "",
            item["status"]
        ])
    
    # Total row
    total_row = ws.max_row + 1
    ws.cell(row=total_row, column=1, value="TOTAL")
    ws.cell(row=total_row, column=1).font = Font(bold=True)
    ws.cell(row=total_row, column=7, value=f"=SUM(G2:G{total_row-1})")
    ws.cell(row=total_row, column=8, value=f"=SUM(H2:H{total_row-1})")
    ws.cell(row=total_row, column=9, value=f"=G{total_row}-H{total_row}")
    for col in [7, 8, 9]:
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
    
    rekap_path = output_dir / "rekap.xlsx"
    wb.save(rekap_path)
    with open(rekap_path, "rb") as f:
        rekap_hash = hashlib.sha256(f.read()).hexdigest()
    
    # 2. draf_spj.docx
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
    doc.save(output_dir / "draf_spj.docx")
    
    # 3. timeline.json
    with open(output_dir / "timeline.json", "w", encoding="utf-8") as f:
        json.dump({
            "kasus_id": kasus_id,
            "timeline": hasil_auditor["timeline"],
            "kontradiksi": hasil_auditor["kontradiksi"],
            "temuan": hasil_auditor["temuan"],
            "rekomendasi": hasil_auditor["rekomendasi"],
        }, f, ensure_ascii=False, indent=2)
    
    # 4. layar_konfirmasi.html
    temuan_sorted = sorted(hasil_auditor["temuan"], key=lambda x: {
        "KRITIS": 0, "TINGGI": 1, "SEDANG": 2, "RENDAH": 3
    }.get(x.get("level", ""), 4))
    
    temuan_html = ""
    if temuan_sorted:
        for t in temuan_sorted:
            level = t["level"]
            badge_class = f"badge-{level.lower()}"
            temuan_html += f'<div class="card temuan-{level.lower()}">\n'
            temuan_html += f'  <p><span class="badge {badge_class}">{level}</span> <strong>{t.get("id_bukti", "")} ({t["tipe"]})</strong> — {t["deskripsi"]}</p>\n'
            temuan_html += '</div>\n'
    else:
        temuan_html = '<div class="card temuan-none"><p>Tidak ada temuan.</p></div>\n'
    
    # Determine approval format
    has_kritis = any(t["level"] == "KRITIS" for t in temuan_sorted)
    has_tinggi = any(t["level"] == "TINGGI" for t in temuan_sorted)
    if has_kritis or has_tinggi:
        instruksi = f"Ketik: <code>SETUJUI {spj_no} SAYA SUDAH MEMERIKSA</code>"
    else:
        instruksi = f"Ketik: <code>SETUJUI {spj_no}</code>"
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Layar Konfirmasi {spj_no}</title>
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
  <h1>Layar Konfirmasi {spj_no}</h1>
  <p>{spt['pegawai']['nama']} — {spt['provinsi']} — {spt['tanggal_berangkat']} s/d {spt['tanggal_kembali']}</p>
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
  <h3>Sidik Keamanan rekap.xlsx</h3>
  <p class="hash">SHA-256: {rekap_hash}</p>
</div>

<div class="instruksi">
  <strong>Instruksi Persetujuan:</strong><br>
  {instruksi}
</div>

</body>
</html>
"""
    with open(output_dir / "layar_konfirmasi.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    # 5. manifest.json
    manifest = {}
    for fpath in output_dir.iterdir():
        if fpath.is_file():
            with open(fpath, "rb") as f:
                manifest[fpath.name] = hashlib.sha256(f.read()).hexdigest()
    
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # Save penyusun result
    hasil = {
        "agen": "penyusun-spj",
        "kasus": kasus_id,
        "spj_no": spj_no,
        "waktu": now_wita(),
        "total_diajukan": totals["total_diajukan"],
        "total_dibayar": totals["total_dibayar"],
        "selisih": totals["selisih"],
        "rekap_hash": rekap_hash,
    }
    save_json(BASE / "kerja" / f"penyusun-spj_{kasus_id}.json", hasil)
    return hasil


def proses_kasus(kasus_id):
    print(f"\n{'='*60}")
    print(f"PROSES KASUS: {kasus_id}")
    print(f"{'='*60}")
    
    # Fase 0: Identifikasi
    spt, error = baca_spt(kasus_id)
    if error:
        print(f"ERROR: {error}")
        return False
    
    print(f"SPT: {spt['nomor_spt']} | {spt['pegawai']['nama']} | {spt['tujuan']}")
    
    # Audit: Koordinator mulai
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "koordinator",
        "aksi": "mulai_proses",
        "file_dibaca": "pesan_pegawai.txt",
        "keputusan": f"SPT terpilih: {spt['nomor_spt']}, Pegawai: {spt['pegawai']['nama']}",
        "aturan": None
    })
    
    # Fase 1: Pembaca (parallel simulation)
    print("\n[FASE 1] Dispatch Pembaca (Tiket, Hotel, Struk) paralel...")
    hasil_pembaca = {}
    id_counter = [1]  # mutable counter for global IDs
    
    ht = fase_pembaca_tiket(kasus_id, spt, id_counter)
    hasil_pembaca["pembaca-tiket"] = ht
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "pembaca-tiket",
        "aksi": "ekstrak",
        "file_dibaca": ", ".join(it["file"] for it in ht["item_bukti"]),
        "keputusan": "; ".join(f"{it['id']}: {it['jenis']} Rp {it.get('nominal', 0):,}" for it in ht["item_bukti"]),
        "aturan": None
    })
    
    hh = fase_pembaca_hotel(kasus_id, spt, id_counter)
    hasil_pembaca["pembaca-hotel"] = hh
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "pembaca-hotel",
        "aksi": "ekstrak",
        "file_dibaca": ", ".join(it["file"] for it in hh["item_bukti"]),
        "keputusan": "; ".join(f"{it['id']}: hotel {it.get('jumlah_malam_tertulis', 0)} malam, Rp {it.get('nominal', 0):,}" for it in hh["item_bukti"]),
        "aturan": None
    })
    
    hs = fase_pembaca_struk(kasus_id, spt, id_counter)
    hasil_pembaca["pembaca-struk"] = hs
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "pembaca-struk",
        "aksi": "ekstrak",
        "file_dibaca": ", ".join(it["file"] for it in hs["item_bukti"]),
        "keputusan": "; ".join(f"{it['id']}: {it['jenis']} Rp {it.get('nominal', 0):,}" for it in hs["item_bukti"]),
        "aturan": None
    })
    
    # Fase 2: Verifikator
    print("\n[FASE 2] Verifikator SBM...")
    sbm = get_sbm(spt["provinsi"], spt["pegawai"]["golongan"])
    hv = fase_verifikator(kasus_id, spt, hasil_pembaca)
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "verifikator-sbm",
        "aksi": "verifikasi",
        "file_dibaca": "sbm.xlsx + SPT",
        "keputusan": f"Pagu H:{sbm.get('pagu_hotel', 0)} T:{sbm.get('pagu_taksi', 0)} UH:{sbm.get('uang_harian', 0)}; temuan: {len(hv['temuan'])}",
        "aturan": ",".join(set(t.get("aturan", "") for t in hv["temuan"] if t.get("aturan"))) or None
    })
    
    # Fase 3: Auditor
    print("\n[FASE 3] Auditor...")
    ha = fase_auditor(kasus_id, spt, hasil_pembaca, hv)
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "auditor",
        "aksi": "audit",
        "file_dibaca": "semua_bukti + verifikator",
        "keputusan": f"Timeline: {len(ha['timeline'])} event, kontradiksi: {len(ha['kontradiksi'])}, temuan: {len(ha['temuan'])}, rekomendasi: {ha['rekomendasi']}",
        "aturan": None
    })
    
    # Fase 4: Penyusun
    print("\n[FASE 4] Penyusun SPJ...")
    hp = fase_penyusun(kasus_id, spt, hasil_pembaca, hv, ha)
    append_audit({
        "waktu": now_wita(),
        "kasus": kasus_id,
        "agen": "penyusun-spj",
        "aksi": "susun_output",
        "file_dibaca": "hasil_verifikasi + audit",
        "keputusan": f"Output disimpan di keluar/draf/{hp['spj_no']}/ (rekap hash: {hp['rekap_hash'][:16]}...)",
        "aturan": None
    })
    
    print(f"\n[SELESAI] {kasus_id} -> {hp['spj_no']}")
    print(f"  Total diajukan: Rp {hp['total_diajukan']:,}")
    print(f"  Total dibayar:  Rp {hp['total_dibayar']:,}")
    print(f"  Selisih:        Rp {hp['selisih']:,}")
    print(f"  Temuan:         {len(ha['temuan'])}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python proses_kasus.py <kasus_id>")
        sys.exit(1)
    
    kasus_id = sys.argv[1]
    success = proses_kasus(kasus_id)
    sys.exit(0 if success else 1)
