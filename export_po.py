#!/usr/bin/env python3
"""
export_po.py — Export PO restock data from KiotViet to clean Excel (.xlsx) files.
"""

import os
from datetime import datetime
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Palette
COLOR_HEADER_BG = "1E293B"      # Dark slate header
COLOR_TABLE_HEAD = "2563EB"     # Royal Blue table header
COLOR_OUT_BG     = "FEE2E2"     # Light Red for 🔴 HẾT HÀNG
COLOR_OUT_TXT    = "991B1B"
COLOR_SOON_BG    = "FEF3C7"     # Light Yellow for 🟡 SẮP HẾT
COLOR_SOON_TXT   = "92400E"
COLOR_TOTAL_BG   = "F1F5F9"

font_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
font_sub = Font(name="Segoe UI", size=10, italic=True, color="64748B")
font_head = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
font_bold = Font(name="Segoe UI", size=10, bold=True)
font_regular = Font(name="Segoe UI", size=10)

font_out = Font(name="Segoe UI", size=10, bold=True, color=COLOR_OUT_TXT)
font_soon = Font(name="Segoe UI", size=10, bold=True, color=COLOR_SOON_TXT)

fill_title = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
fill_head = PatternFill(start_color=COLOR_TABLE_HEAD, end_color=COLOR_TABLE_HEAD, fill_type="solid")
fill_out = PatternFill(start_color=COLOR_OUT_BG, end_color=COLOR_OUT_BG, fill_type="solid")
fill_soon = PatternFill(start_color=COLOR_SOON_BG, end_color=COLOR_SOON_BG, fill_type="solid")
fill_total = PatternFill(start_color=COLOR_TOTAL_BG, end_color=COLOR_TOTAL_BG, fill_type="solid")

thin_border = Border(
    left=Side(style='thin', color='CBD5E1'),
    right=Side(style='thin', color='CBD5E1'),
    top=Side(style='thin', color='CBD5E1'),
    bottom=Side(style='thin', color='CBD5E1')
)
top_thick_bottom_double = Border(
    top=Side(style='thin', color='475569'),
    bottom=Side(style='double', color='475569')
)

align_center = Alignment(horizontal='center', vertical='center')
align_left = Alignment(horizontal='left', vertical='center')
align_right = Alignment(horizontal='right', vertical='center')

def create_po_sheet(ws, sheet_title, items, cover_days=30):
    ws.views.sheetView[0].showGridLines = True

    # 1. Title Block
    ws.merge_cells("A1:H1")
    cell_title = ws["A1"]
    cell_title.value = f"ĐƠN ĐẶT HÀNG NHẬP KHO (PURCHASE ORDER) — {sheet_title.upper()}"
    cell_title.font = font_title
    cell_title.fill = fill_title
    cell_title.alignment = align_center
    ws.row_dimensions[1].height = 36

    # Sub info
    today_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws.merge_cells("A2:H2")
    cell_sub = ws["A2"]
    cell_sub.value = f"Ngày khởi tạo: {today_str} | Target dự trữ: {cover_days} ngày | Đơn vị: Combomacbook / Lucas.vn"
    cell_sub.font = font_sub
    cell_sub.alignment = align_center
    ws.row_dimensions[2].height = 20

    ws.row_dimensions[3].height = 10

    # Table Headers
    headers = [
        ("STT", 6, align_center),
        ("Thương Hiệu / NPP", 18, align_left),
        ("Mã SP (SKU)", 16, align_left),
        ("Tên Sản Phẩm", 45, align_left),
        ("Tồn Kho", 10, align_right),
        ("Bán/Ngày", 10, align_right),
        ("SL Nhập Gợi Ý", 14, align_right),
        ("Trạng Thái", 14, align_center)
    ]

    ws.row_dimensions[4].height = 26
    for col_idx, (h_name, _, h_align) in enumerate(headers, start=1):
        c = ws.cell(row=4, column=col_idx, value=h_name)
        c.font = font_head
        c.fill = fill_head
        c.alignment = h_align
        c.border = thin_border

    # Data Rows
    start_row = 5
    for idx, item in enumerate(items, start=1):
        row_idx = start_row + idx - 1
        ws.row_dimensions[row_idx].height = 22

        is_out = item.get("oh", 0) <= 0
        st_text = "🔴 HẾT HÀNG" if is_out else f"🟡 Còn {item.get('dleft', 0):.0f} ngày"
        row_font = font_out if is_out else font_soon
        row_fill = fill_out if is_out else fill_soon

        values = [
            (idx, align_center, None),
            (item.get("brand", "Khác"), align_left, None),
            (item.get("code", ""), align_left, None),
            (item.get("name", ""), align_left, None),
            (item.get("oh", 0), align_right, "#,##0"),
            (item.get("vel", 0.0), align_right, "0.0"),
            (item.get("need", 0), align_right, "#,##0"),
            (st_text, align_center, None)
        ]

        for col_idx, (val, alignment, num_fmt) in enumerate(values, start=1):
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            c.font = font_bold if col_idx in (1, 3, 7) else font_regular
            c.alignment = alignment
            c.border = thin_border
            if num_fmt:
                c.number_format = num_fmt
            if col_idx == 8: # Highlight status cell
                c.font = row_font
                c.fill = row_fill

    # Total Row
    tot_row = start_row + len(items)
    ws.row_dimensions[tot_row].height = 25
    ws.merge_cells(start_row=tot_row, start_column=1, end_row=tot_row, end_column=4)
    cell_tot_label = ws.cell(row=tot_row, column=1, value=f"TỔNG CỘNG ({len(items)} SẢN PHẨM)")
    cell_tot_label.font = font_bold
    cell_tot_label.alignment = align_right

    for c_idx in range(1, 9):
        c = ws.cell(row=tot_row, column=c_idx)
        c.fill = fill_total
        c.border = top_thick_bottom_double

    # Sum formulas for Stock & Needed PO Qty
    c_oh = ws.cell(row=tot_row, column=5, value=f"=SUM(E{start_row}:E{tot_row-1})")
    c_oh.font = font_bold
    c_oh.alignment = align_right
    c_oh.number_format = "#,##0"

    c_need = ws.cell(row=tot_row, column=7, value=f"=SUM(G{start_row}:G{tot_row-1})")
    c_need.font = font_bold
    c_need.alignment = align_right
    c_need.number_format = "#,##0"

    # Set Column Widths
    for col_idx, (_, min_w, _) in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min_w


BRANDS_LIST = ["AhaStyle", "Anank", "Anker", "Aulumu", "Baseus", "BMX", "Coteetci", "Divoom",
               "Elago", "HODA", "HyperWork", "Hyper", "IDMIX", "inateck", "Innostyle", "JCPAL",
               "Jinya", "JOWAY", "JRC", "LISEN", "Lofree", "Lucas", "Maxco", "Mipow", "Mocoll",
               "Nillkin", "NJOYNY", "Pitaka", "Satechi", "Sharge", "SKINARMA", "Thule", "Tomtoc",
               "Torras", "Ulanzi", "Urr", "WIWU", "Zagg"]
_BRANDS_SORTED = sorted(BRANDS_LIST, key=len, reverse=True)

def get_brand(item):
    if item.get("brand"):
        return item["brand"]
    name_low = (item.get("name") or "").lower()
    for b in _BRANDS_SORTED:
        if b.lower() in name_low:
            return b
    return "Khác"

def export_po_excel(out_items, soon_items, output_dir="po_exports", cover_days=30):
    """
    Xuất danh sách sản phẩm ra file Excel (.xlsx) chuẩn PO.
    Trả về dict: {"master_file": path, "brand_files": {brand: path}}
    """
    os.makedirs(output_dir, exist_ok=True)
    today_stamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Combined list
    all_items = []
    for r in out_items:
        all_items.append(dict(r, crit=0, st="HẾT", brand=get_brand(r)))
    for r in soon_items:
        all_items.append(dict(r, crit=1, st=f"{r['dleft']:.0f}d", brand=get_brand(r)))

    if not all_items:
        print("[!] Không có sản phẩm cần nhập -> Không tạo file Excel.")
        return None

    # Group by brand
    brand_groups = defaultdict(list)
    for it in all_items:
        brand = it["brand"]
        brand_groups[brand].append(it)

    # Sort items within brand groups
    for b in brand_groups:
        brand_groups[b].sort(key=lambda i: (i["crit"], -i["vel"]))

    # 1. Create Master Workbook with multiple sheets
    wb_master = openpyxl.Workbook()
    ws_all = wb_master.active
    ws_all.title = "TẤT CẢ NPP"
    create_po_sheet(ws_all, "TỔNG HỢP CẢNH BÁO KHO", all_items, cover_days=cover_days)

    # Sort brands by number of urgent items
    sorted_brands = sorted(brand_groups.keys(), key=lambda b: (-sum(1 for i in brand_groups[b] if i["crit"] == 0), -len(brand_groups[b])))

    brand_files = {}

    for b in sorted_brands:
        items = brand_groups[b]
        clean_title = str(b)[:30].replace("/", "-").replace("\\", "-").replace(":", "")
        
        # Add sheet to master workbook
        ws_b = wb_master.create_sheet(title=clean_title)
        create_po_sheet(ws_b, f"NPP {b}", items, cover_days=cover_days)

        # 2. Create individual Workbook per brand for direct sending
        wb_b = openpyxl.Workbook()
        ws_single = wb_b.active
        ws_single.title = clean_title
        create_po_sheet(ws_single, f"NPP {b}", items, cover_days=cover_days)

        file_b_path = os.path.join(output_dir, f"PO_{clean_title}_{today_stamp}.xlsx")
        wb_b.save(file_b_path)
        brand_files[b] = file_b_path

    master_path = os.path.join(output_dir, f"PO_TONG_HOP_{today_stamp}.xlsx")
    wb_master.save(master_path)

    print(f"[+] Đã xuất Master PO: {master_path}")
    print(f"[+] Đã xuất {len(brand_files)} file PO riêng theo Thương Hiệu trong folder '{output_dir}/'")

    return {
        "master_file": master_path,
        "brand_files": brand_files
    }

if __name__ == "__main__":
    # Quick test mock data
    sample_out = [
        {"code": "TOMTOC01", "name": "Balo Tomtoc A42 MacBook 16 inch", "brand": "Tomtoc", "oh": 0, "vel": 1.5, "dleft": 0, "need": 45},
        {"code": "THULE02", "name": "Balo Thule Subterra 26L Black", "brand": "Thule", "oh": 0, "vel": 0.8, "dleft": 0, "need": 24}
    ]
    sample_soon = [
        {"code": "WIWU03", "name": "Túi Chống Sốc WiWU Pilot Sleeve 14 inch", "brand": "WIWU", "oh": 3, "vel": 0.5, "dleft": 6.0, "need": 12}
    ]
    export_po_excel(sample_out, sample_soon)
