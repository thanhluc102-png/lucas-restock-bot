# Lucas Restock Alert Bot

Bot cảnh báo Telegram sản phẩm **sắp hết hàng** cho shop KiotViet (`combomacbook`), để nhắc nhập hàng.

## Cách hoạt động
1. Lấy **vận tốc bán** `LOOKBACK_DAYS` ngày qua từ hóa đơn KiotViet (bỏ hóa đơn hủy).
2. Lấy **tồn kho hiện tại** (onHand) của từng sản phẩm.
3. Tính **số ngày còn bán được** = tồn / (bán mỗi ngày), rồi cảnh báo:
   - 🔴 **HẾT hàng mà đang bán** → nhập gấp
   - 🟡 **SẮP hết** (còn ≤ `SOON_DAYS` ngày)
   - kèm gợi ý **lượng nên nhập** = đủ bán `COVER_DAYS` ngày.

## Lịch chạy
GitHub Actions cron `25 1 * * *` (~08:25 sáng VN), gửi qua Telegram bot **@LucasStravaBot**.

## Secrets cần đặt (Settings → Secrets → Actions)
`KIOT_CLIENT_ID`, `KIOT_CLIENT_SECRET`, `KIOT_RETAILER`, `TG_TOKEN`, `TG_CHAT_ID`.

## Chỉnh ngưỡng
Sửa trong `.github/workflows/restock.yml`: `SOON_DAYS` (ngày cảnh báo), `MIN_VEL` (bỏ sp bán chậm), `COVER_DAYS` (nhập đủ bán bao nhiêu ngày), `LOOKBACK_DAYS` (cửa sổ tính vận tốc).

## Chạy tay
```bash
pip install requests
KIOT_CLIENT_ID=... KIOT_CLIENT_SECRET=... KIOT_RETAILER=combomacbook \
TG_TOKEN=... TG_CHAT_ID=... python restock_bot.py
```
