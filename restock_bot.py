#!/usr/bin/env python3
"""
restock_bot.py — Cảnh báo Telegram sản phẩm sắp hết hàng cho shop KiotViet (combomacbook).

Logic: lấy tồn kho hiện tại (onHand) + vận tốc bán N ngày qua (từ hóa đơn) ->
tính số ngày còn bán được -> báo:
  🔴 HẾT hàng mà đang bán (nhập gấp)
  🟡 SẮP hết (còn ≤ SOON_DAYS ngày)
kèm gợi ý lượng nên nhập = đủ bán COVER_DAYS ngày.

Chạy: python restock_bot.py   (cấu hình qua biến môi trường / GitHub Secrets)
"""
import os, time, sys, html
from datetime import datetime, timedelta
from collections import defaultdict
import requests

# ---- Cấu hình (env) ----
CID = os.getenv("KIOT_CLIENT_ID"); CS = os.getenv("KIOT_CLIENT_SECRET")
RETAILER = os.getenv("KIOT_RETAILER", "combomacbook")
TG_TOKEN = os.getenv("TG_TOKEN"); TG_CHAT = os.getenv("TG_CHAT_ID")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))   # cửa sổ tính vận tốc bán
SOON_DAYS     = int(os.getenv("SOON_DAYS", "14"))       # còn ≤ ngày này thì cảnh báo
MIN_VEL       = float(os.getenv("MIN_VEL", "0.1"))      # bỏ sp bán chậm hơn ngần này/ngày
COVER_DAYS    = int(os.getenv("COVER_DAYS", "30"))      # gợi ý nhập đủ bán bao nhiêu ngày
MAX_LIST      = int(os.getenv("MAX_LIST", "40"))        # tối đa mỗi nhóm trong tin

KIOT = "https://public.kiotapi.com"

# Thương hiệu (từ KiotViet /trademark) — khớp theo tên sp. Dài trước để "HyperWork" thắng "Hyper".
BRANDS = ["AhaStyle", "Anank", "Anker", "Aulumu", "Baseus", "BMX", "Coteetci", "Divoom",
          "Elago", "HODA", "HyperWork", "Hyper", "IDMIX", "inateck", "Innostyle", "JCPAL",
          "Jinya", "JOWAY", "JRC", "LISEN", "Lofree", "Lucas", "Maxco", "Mipow", "Mocoll",
          "Nillkin", "NJOYNY", "Pitaka", "Satechi", "Sharge", "SKINARMA", "Thule", "Tomtoc",
          "Torras", "Ulanzi", "Urr", "WIWU", "Zagg"]
_BRANDS_SORTED = sorted(BRANDS, key=len, reverse=True)


def brand_of(name):
    low = (name or "").lower()
    for b in _BRANDS_SORTED:
        if b.lower() in low:
            return b
    return "Khác"


def get_token():
    r = requests.post("https://id.kiotviet.vn/connect/token",
                      data={"grant_type": "client_credentials", "client_id": CID,
                            "client_secret": CS, "scope": "PublicApi.Access"},
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def sales_by_code(h):
    """Tổng số lượng bán mỗi mã trong LOOKBACK_DAYS (bỏ hóa đơn hủy status==2)."""
    frm = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    to  = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    sold = defaultdict(float); cur = 0; total = None
    while True:
        d = requests.get(f"{KIOT}/invoices", headers=h, timeout=60,
                         params={"pageSize": 100, "currentItem": cur,
                                 "fromPurchaseDate": frm, "toPurchaseDate": to}).json()
        total = d.get("total"); data = d.get("data") or []
        if not data:
            break
        for inv in data:
            if inv.get("status") == 2:   # Đã hủy
                continue
            for it in inv.get("invoiceDetails") or []:
                sold[it.get("productCode")] += (it.get("quantity") or 0)
        cur += len(data)
        if total is None or cur >= total:
            break
        time.sleep(0.04)
    return sold


def products_onhand(h):
    prods = {}; cur = 0; total = None
    while True:
        d = requests.get(f"{KIOT}/products", headers=h, timeout=45,
                         params={"pageSize": 100, "currentItem": cur, "includeInventory": "true"}).json()
        total = d.get("total"); data = d.get("data") or []
        if not data:
            break
        for p in data:
            oh = sum((iv.get("onHand") or 0) for iv in (p.get("inventories") or []))
            prods[p.get("code")] = {"name": p.get("fullName") or p.get("name"),
                                    "onHand": oh, "active": p.get("isActive")}
        cur += len(data)
        if total is None or cur >= total:
            break
        time.sleep(0.04)
    return prods


def build(sold, prods):
    out, soon = [], []
    for code, qty in sold.items():
        p = prods.get(code)
        if not p or not p.get("active"):
            continue
        vel = qty / LOOKBACK_DAYS
        if vel < MIN_VEL:
            continue
        oh = p["onHand"]; dleft = oh / vel if vel > 0 else 9999
        need = max(0, round(vel * COVER_DAYS - oh))
        rec = {"code": code, "name": p["name"], "oh": oh, "vel": round(vel, 1),
               "dleft": dleft, "need": need, "qty": int(qty)}
        if oh <= 0:
            out.append(rec)
        elif dleft <= SOON_DAYS:
            soon.append(rec)
    out.sort(key=lambda r: -r["vel"])
    soon.sort(key=lambda r: r["dleft"])
    return out, soon


def esc(s):
    return html.escape(str(s))


def _table(rows, cols):
    """Bảng monospace canh cột. cols = [(tiêu đề, độ rộng, key, canh_phải?)]."""
    def cell(v, w, right):
        v = str(v)
        if len(v) > w:
            v = v[:w-1] + "…"
        return v.rjust(w) if right else v.ljust(w)
    head = " ".join(cell(t, w, r) for t, w, k, r in cols)
    out = [head, "-" * len(head)]
    for row in rows:
        out.append(" ".join(cell(row[k], w, r) for t, w, k, r in cols))
    return "<pre>" + esc("\n".join(out)) + "</pre>"


def render(out, soon):
    """Gom theo THƯƠNG HIỆU (để đặt hàng từng nhà cung cấp). Mỗi tin gộp nhiều brand, không cắt <pre>."""
    today = datetime.now().strftime("%d/%m/%Y")
    header = (f"<b>📦 CẢNH BÁO NHẬP HÀNG — {today}</b>\n"
              f"<i>Vận tốc bán {LOOKBACK_DAYS} ngày · gợi ý nhập đủ bán {COVER_DAYS} ngày · 🔴 hết · 🟡 sắp hết</i>")
    if not out and not soon:
        return [header + "\n\n✅ Không có sản phẩm nào sắp hết. Kho ổn định."]

    # gộp 2 nhóm, gắn trạng thái + brand
    items = []
    for r in out:
        items.append(dict(r, st="HẾT", crit=0, brand=brand_of(r["name"])))
    for r in soon:
        items.append(dict(r, st=f"{r['dleft']:.0f}d", crit=1, brand=brand_of(r["name"])))

    groups = defaultdict(list)
    for it in items:
        groups[it["brand"]].append(it)
    # brand nhiều "hết hàng" nhất lên trước, rồi theo tổng cần nhập
    order = sorted(groups, key=lambda b: (-sum(1 for i in groups[b] if i["crit"] == 0),
                                          -sum(i["need"] for i in groups[b])))
    cols = [("Mã", 12, "code", False), ("TT", 4, "st", True), ("Tồn", 4, "oh", True),
            ("Bán", 4, "vel", True), ("Nhập", 5, "need", True), ("Tên", 20, "name", False)]

    blocks = []
    total_urgent = sum(1 for i in items if i["crit"] == 0)
    for b in order:
        g = sorted(groups[b], key=lambda i: (i["crit"], -i["vel"]))
        n_out = sum(1 for i in g if i["crit"] == 0)
        tag = f"🏷️ <b>{esc(b)}</b> ({len(g)} sp{', ' + str(n_out) + ' hết' if n_out else ''})"
        blocks.append(tag + "\n" + _table(g, cols))

    # đóng gói: header + các block, sang tin mới khi gần 3800 ký tự (không cắt giữa block)
    parts = [f"{header}\n\n<b>Tổng: {len(items)} sp cần nhập</b> · 🔴 {total_urgent} hết hàng · {len(order)} thương hiệu"]
    buf = ""
    for blk in blocks:
        if len(buf) + len(blk) + 2 > 3800:
            if buf:
                parts.append(buf)
            buf = ""
        buf += ("\n\n" if buf else "") + blk
    if buf:
        parts.append(buf)
    return parts


def send_telegram(parts):
    for part in parts:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          json={"chat_id": TG_CHAT, "text": part, "parse_mode": "HTML",
                                "disable_web_page_preview": True}, timeout=30)
        if not r.ok:
            print("Telegram lỗi:", r.status_code, r.text[:200])
        time.sleep(0.5)


def main():
    missing = [k for k, v in {"KIOT_CLIENT_ID": CID, "KIOT_CLIENT_SECRET": CS,
                              "TG_TOKEN": TG_TOKEN, "TG_CHAT_ID": TG_CHAT}.items() if not v]
    if missing:
        print("Thiếu env:", missing); sys.exit(1)
    tok = get_token()
    h = {"Retailer": RETAILER, "Authorization": f"Bearer {tok}"}
    sold = sales_by_code(h)
    prods = products_onhand(h)
    out, soon = build(sold, prods)
    parts = render(out, soon)
    print(f"🔴 {len(out)} hết hàng | 🟡 {len(soon)} sắp hết | gửi Telegram ({len(parts)} tin)…")
    send_telegram(parts)
    print("Xong.")


if __name__ == "__main__":
    main()
