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


def render(out, soon):
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [f"<b>📦 CẢNH BÁO NHẬP HÀNG — {today}</b>",
             f"<i>Vận tốc bán {LOOKBACK_DAYS} ngày · gợi ý nhập đủ bán {COVER_DAYS} ngày</i>", ""]
    if not out and not soon:
        lines.append("✅ Không có sản phẩm nào sắp hết. Kho ổn định.")
        return "\n".join(lines)
    if out:
        lines.append(f"🔴 <b>HẾT HÀNG mà đang bán ({len(out)}) — NHẬP GẤP</b>")
        for r in out[:MAX_LIST]:
            lines.append(f"• <b>{esc(r['code'])}</b> {esc(r['name'][:44])}\n"
                         f"   bán {r['vel']}/ngày · tồn {r['oh']} · <b>nhập ~{r['need']}</b>")
        if len(out) > MAX_LIST:
            lines.append(f"   …và {len(out)-MAX_LIST} sp khác")
        lines.append("")
    if soon:
        lines.append(f"🟡 <b>SẮP HẾT (≤{SOON_DAYS} ngày) ({len(soon)})</b>")
        for r in soon[:MAX_LIST]:
            lines.append(f"• <b>{esc(r['code'])}</b> {esc(r['name'][:44])}\n"
                         f"   còn <b>{r['dleft']:.1f} ngày</b> · tồn {r['oh']} · bán {r['vel']}/ngày · nhập ~{r['need']}")
        if len(soon) > MAX_LIST:
            lines.append(f"   …và {len(soon)-MAX_LIST} sp khác")
    return "\n".join(lines)


def send_telegram(text):
    # Telegram giới hạn 4096 ký tự/tin -> cắt thành nhiều tin
    parts, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > 3800:
            parts.append(buf); buf = ""
        buf += line + "\n"
    if buf:
        parts.append(buf)
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
    text = render(out, soon)
    print(f"🔴 {len(out)} hết hàng | 🟡 {len(soon)} sắp hết | gửi Telegram…")
    send_telegram(text)
    print("Xong.")


if __name__ == "__main__":
    main()
