# GUARDIAN Blockchain Evidence System

Lưu trữ bằng chứng bạo lực học đường bất biến trên **Hardhat local blockchain** + **IPFS (Pinata)**.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────────┐
│   Frontend  │────▶│ Flask (:5000)│────▶│ Node.js (:5001)    │
│  index.html │     │  app.py      │     │  blockchain/server.js │
└─────────────┘     └──────────────┘     └────────┬───────────┘
                                                  │
                               ┌──────────────────┼──────────────────┐
                               ▼                                     ▼
                    ┌──────────────────┐               ┌──────────────────┐
                    │  IPFS (Pinata)  │               │ Hardhat (:8545)  │
                    │  Lưu file gốc   │               │  EvidenceNFT.sol │
                    └──────────────────┘               └──────────────────┘
```

## Quick Start

### 1. Cài đặt Node.js service

```bash
cd web/blockchain
npm install
```

### 2. Setup Hardhat local blockchain

```bash
# Khởi tạo project
npx hardhat init
# Copy và cấu hình .env
copy .env.example .env
```

Chỉnh sửa `.env`:

```env
HARDHAT_RPC_URL=http://127.0.0.1:8545
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CONTRACT_ADDRESS=
PINATA_JWT=your_pinata_jwt_here
```

### 3. Deploy smart contract

```bash
# Terminal 1: Chạy Hardhat node
npx hardhat node
# Output: Accounts + RPC URL (http://127.0.0.1:8545)

# Terminal 2: Deploy contract
npx hardhat deploy --network localhost
# Output: Contract deployed at: 0x... → ghi vào .env
# CONTRACT_ADDRESS=0x...
```

### 4. Chạy Node.js service

```bash
# Tiếp tục từ Terminal 2
node server.js
# Listening on http://localhost:5001
```

### 5. Chạy Flask app

```bash
# Terminal 3
cd web
pip install flask flask-cors requests
python app.py
# Dashboard: http://localhost:5000
```

## Flow hoạt động

1. **Bật webcam** → YOLO phát hiện bạo lực
2. Nhấn **"Capture Frame"** → chụp ảnh detection frame
3. Flask gửi sang Node.js service:
   - Upload file lên **IPFS** → nhận CID bất biến
   - Mint **EvidenceNFT** lên Hardhat → nhận tokenId + txHash
4. Frontend hiển thị: SHA-256 hash, IPFS CID, blockchain token ID
5. **Xác thực**: hash file gốc luôn khớp với chain — chống giả mạo

## Endpoints

| Method | URL | Mô tả |
|--------|-----|-------|
| POST | `/api/evidence/save` | Lưu bằng chứng (Flask bridge) |
| GET | `/api/evidence/list` | Danh sách file local |
| POST | `localhost:5001/api/evidence/save` | Lưu trực tiếp lên IPFS + chain |
| GET | `localhost:5001/api/evidence/:tokenId` | Truy vấn bằng chứng |
| GET | `localhost:5001/api/evidence/verify/:tokenId?hash=xxx` | Xác thực hash |

## Smart Contract

**EvidenceNFT** lưu trữ:
- `tokenId` — ID NFT duy nhất
- `ipfsCID` — CID file gốc trên IPFS
- `sha256Hash` — SHA-256 file gốc
- `eventTimestamp` — thời điểm sự kiện
- `blockTimestamp` — thời điểm mint lên chain
- `metadata` — JSON: class, confidence, bbox...

**Tính bất biến**: Không có function `deleteEvidence` hay `updateEvidence`. Một khi mint, dữ liệu tồn tại vĩnh viễn trên blockchain.

## Không bắt buộc blockchain?

Nếu chỉ muốn lưu local + IPFS (không cần blockchain):
- Bỏ qua bước 2, 3
- Bỏ qua `CONTRACT_ADDRESS` trong `.env`
- Node.js service sẽ tự skip mint, chỉ upload IPFS
