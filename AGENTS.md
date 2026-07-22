# Global Agent Rules & Knowledge Base

## 📦 KiotViet Restock Bot & Distributor (NPP) Mapping Rules

### 1. Brand-to-Distributor (NPP) & Credit Term Mapping
- **HD**: Thule, Innostyle, Tomtoc, BMX, Hyper, Mipow — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)
- **3HVN**: HyperWork — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)
- **Viettel Distribution**: Anker — **Thanh toán ngay (0 ngày)** (Chia làm 2 đợt nhập, mỗi đợt 14 ngày)
- **iFuture**: Aulumu, Lisen — **Công nợ 2 tuần (14 ngày)** (Nhập vừa đủ 2-3 tuần)
- **ACE**: JRC, Inateck — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)
- **Senco**: JCPAL, IDMIX, Mocoll — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)
- **Tuấn Anh**: Hoda, Joway, Maxco, Nillkin, WIWU — **Công nợ 60 ngày** (Đòn bẩy tối đa, nhập đủ 100% nhu cầu)
- **DTR**: Pitaka, Zagg — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)
- **TLC**: Uniq, Skinarma — **Công nợ 2 tuần (14 ngày)** (Nhập vừa đủ 2-3 tuần)
- **Huy Linh**: Ulanzi — **Công nợ 2 tuần (14 ngày)** (Nhập vừa đủ 2-3 tuần)
- **Lucas**: Lucas — **Thanh toán ngay (0 ngày)** (Chia làm 2 đợt nhập, mỗi đợt 14 ngày)
- **StreamCast**: Satechi, Sharge — **Công nợ 30 ngày** (Ưu tiên nhập 100% nhu cầu 30 ngày)

### 2. Restock Velocity Calculation Algorithm
- **When `onHand == 0` (Out of Stock)**:
  - MUST calculate velocity using **Peak 7-day Window**: slide a 7-day window over the 60 days of sales history prior to running out of stock, and take the window with MAXIMUM sales volume.
  - Reason: Avoids the "trickle sales" trap (bẫy đơn bán lẻ giọt đắng) when stock is nearly depleted and sales drop due to lack of inventory.
- **When `onHand > 0` (In Stock)**:
  - Calculate velocity over `LOOKBACK_DAYS` (default 30 days) from current date.

### 3. Telegram Stock Notification Group
- Target Telegram Group: **LucasStock**
- **Chat ID**: `-5352305526`
- **Bot Token**: `8242451016:AAEvo3IxhdEqZm20GM2QjZ_DrFfaC5jEva4`

### 4. Cash Flow & Platform Payout Delay Rules
- **Shopee / TikTok Shop Payout**: 14-day delay before sales revenue clears into bank account.
- **Cash Reserve Requirement**: Preserve **130 - 150 million VNĐ** cash buffer in bank account for operational expenses, shipping, and Ads.
