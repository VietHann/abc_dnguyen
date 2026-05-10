/**
 * GUARDIAN Blockchain Service
 * Node.js service để:
 *   1. Upload file (image/video) lên IPFS qua Pinata
 *   2. Mint EvidenceNFT lên Hardhat local blockchain
 *   3. Trả kết quả (CID, transaction hash, tokenId, chain info) về cho Flask
 */

import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { createHash } from "crypto";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { createRequire } from "module";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config();

// BigInt-safe JSON serializer for Express
const bigIntReplacer = (key, value) => {
  if (typeof value === "bigint") return String(value);
  if (value && typeof value === "object" && value.type === "BigInt") return String(value);
  return value;
};

const originalJson = express.response.json;
express.response.json = function (data) {
  return originalJson.call(this, JSON.parse(JSON.stringify(data, bigIntReplacer)));
};

const app = express();
app.use(cors());
app.use(express.json({ limit: "500mb" }));
app.use(express.urlencoded({ extended: true, limit: "500mb" }));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Tính SHA-256 hash của file buffer
 */
function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

/**
 * Upload file lên IPFS qua Pinata REST API (không cần SDK)
 */
async function uploadToIPFS(fileBuffer, filename, mimeType) {
  const jwt = process.env.PINATA_JWT;
  if (!jwt) {
    throw new Error("PINATA_JWT not configured in .env");
  }

  const formData = new FormData();
  const blob = new Blob([fileBuffer], { type: mimeType });
  formData.append("file", blob, filename);

  const pinataMeta = {
    name: `GUARDIAN_EVIDENCE_${Date.now()}_${filename}`,
    keyvalues: {
      system: "GUARDIAN",
      timestamp: new Date().toISOString(),
    },
  };
  formData.append("pinataMetadata", JSON.stringify(pinataMeta));

  const pinataOptions = {
    cidVersion: 1,
  };
  formData.append("pinataOptions", JSON.stringify(pinataOptions));

  const resp = await fetch("https://api.pinata.cloud/pinning/pinFileToIPFS", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${jwt}`,
    },
    body: formData,
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Pinata upload failed: ${err}`);
  }

  const data = await resp.json();
  return {
    cid: data.IpfsHash,
    size: data.PinSize,
    gatewayUrl: `https://gateway.pinata.cloud/ipfs/${data.IpfsHash}`,
  };
}

/**
 * Mint evidence lên Hardhat local blockchain
 */
async function mintToBlockchain(ipfsCID, fileHash, eventTimestamp, metadata, ipfsGateway) {
  const rpcUrl = process.env.HARDHAT_RPC_URL || "http://127.0.0.1:8545";
  const privateKey = process.env.PRIVATE_KEY;
  const contractAddress = process.env.CONTRACT_ADDRESS;

  if (!contractAddress) {
    throw new Error("CONTRACT_ADDRESS not configured. Run: npx hardhat deploy");
  }
  if (!privateKey) {
    throw new Error("PRIVATE_KEY not configured in .env");
  }

  // Dùng viem để gọi contract (không cần ethers vì contract compile sẵn)
  const { createPublicClient, createWalletClient, http, encodeFunctionData, parseEther } = await import("viem");
  const { privateKeyToAccount } = await import("viem/accounts");
  const { hardhat } = await import("viem/chains");

  const account = privateKeyToAccount(privateKey);
  const publicClient = createPublicClient({
    chain: hardhat,
    transport: http(rpcUrl),
  });
  const walletClient = createWalletClient({
    account,
    chain: hardhat,
    transport: http(rpcUrl),
  });

  // ABI minimal để call mintEvidence
  const abi = [
    {
      type: "function",
      name: "mintEvidence",
      inputs: [
        { name: "eventTimestamp", type: "uint256" },
        { name: "ipfsCID", type: "string" },
        { name: "sha256Hash", type: "string" },
        { name: "metadata", type: "string" },
      ],
      outputs: [{ name: "tokenId", type: "uint256" }],
      stateMutability: "nonpayable",
    },
  ];

  const { request } = await publicClient.simulateContract({
    address: contractAddress,
    abi,
    functionName: "mintEvidence",
    args: [
      BigInt(eventTimestamp),
      ipfsCID,
      fileHash,
      metadata,
    ],
    account,
  });

  const txHash = await walletClient.writeContract(request);

  // Đợi transaction confirm
  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });

  // Lấy tokenId: đọc totalEvidence từ contract (trustworthy)
  let tokenId = null;
  try {
    const total = await publicClient.readContract({
      address: contractAddress,
      abi: [
        {
          type: "function",
          name: "totalEvidence",
          outputs: [{ type: "uint256" }],
        },
      ],
      functionName: "totalEvidence",
    });
    tokenId = String(total);
  } catch (_) {
    // Không đọc được, trả null
  }

  return {
    txHash,
    blockNumber: Number(receipt.blockNumber),
    contractAddress,
    tokenId,
    explorerUrl: `http://localhost:8545/tx/${txHash}`,
  };
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

/**
 * POST /api/evidence/save
 * Body: {
 *   "file": base64 string,
 *   "filename": "incident_001.jpg",
 *   "mimeType": "image/jpeg",
 *   "eventTimestamp": 1715000000,
 *   "metadata": { class: "violence", confidence: 0.92, bbox: [...] }
 * }
 */
app.post("/api/evidence/save", async (req, res) => {
  try {
    const { file, filename, mimeType, eventTimestamp, metadata } = req.body;

    if (!file || !filename) {
      return res.status(400).json({ success: false, error: "Missing file or filename" });
    }

    const fileBuffer = Buffer.from(file, "base64");
    const fileHash = sha256(fileBuffer);
    const ts = eventTimestamp || Math.floor(Date.now() / 1000);
    const metaStr = typeof metadata === "string" ? metadata : JSON.stringify(metadata || {});

    console.log(`[EVIDENCE] Processing: ${filename} (${(fileBuffer.length / 1024).toFixed(1)} KB)`);
    console.log(`[EVIDENCE] SHA-256: ${fileHash}`);

    // 1. Upload lên IPFS
    let ipfsResult = null;
    let ipfsError = null;
    if (process.env.PINATA_JWT) {
      try {
        ipfsResult = await uploadToIPFS(fileBuffer, filename, mimeType || "application/octet-stream");
        console.log(`[EVIDENCE] IPFS CID: ${ipfsResult.cid}`);
      } catch (e) {
        ipfsError = e.message;
        console.warn(`[EVIDENCE] IPFS upload failed: ${e.message}`);
      }
    } else {
      console.log("[EVIDENCE] PINATA_JWT not set — skipping IPFS upload");
    }

    // 2. Mint lên blockchain
    let chainResult = null;
    let chainError = null;
    if (process.env.CONTRACT_ADDRESS) {
      try {
        const ipfsCID = ipfsResult?.cid || "no-ipfs-cid";
        chainResult = await mintToBlockchain(
          ipfsCID,
          fileHash,
          ts,
          metaStr,
          process.env.PINATA_GATEWAY
        );
        console.log(`[EVIDENCE] Chain tokenId: ${chainResult.tokenId}, tx: ${chainResult.txHash}`);
      } catch (e) {
        chainError = e.message;
        console.warn(`[EVIDENCE] Blockchain mint failed: ${e.message}`);
      }
    } else {
      console.log("[EVIDENCE] CONTRACT_ADDRESS not set — skipping blockchain mint");
    }

    const response = {
      success: true,
      filename,
      fileHash,
      fileSize: fileBuffer.length,
      ipfs: ipfsResult || { skipped: true, reason: ipfsError || "PINATA_JWT not configured" },
      blockchain: chainResult
        ? {
            ...chainResult,
            status: "minted",
          }
        : { skipped: true, reason: chainError || "CONTRACT_ADDRESS not configured" },
      timestamp: new Date().toISOString(),
    };

    return res.json(response);
  } catch (e) {
    console.error("[EVIDENCE] Error:", e);
    return res.status(500).json({ success: false, error: e.message });
  }
});

/**
 * GET /api/evidence/:tokenId
 * Truy vấn bằng chứng từ blockchain
 */
app.get("/api/evidence/:tokenId", async (req, res) => {
  try {
    const { tokenId } = req.params;
    const rpcUrl = process.env.HARDHAT_RPC_URL || "http://127.0.0.1:8545";
    const contractAddress = process.env.CONTRACT_ADDRESS;

    if (!contractAddress) {
      return res.status(400).json({ success: false, error: "CONTRACT_ADDRESS not configured" });
    }

    const { createPublicClient, http } = await import("viem");
    const { hardhat } = await import("viem/chains");

    const client = createPublicClient({
      chain: hardhat,
      transport: http(rpcUrl),
    });

    const evidence = await client.readContract({
      address: contractAddress,
      abi: [
        {
          type: "function",
          name: "getEvidence",
          inputs: [{ name: "tokenId", type: "uint256" }],
          outputs: [
            {
              type: "tuple",
              components: [
                { name: "tokenId",        type: "uint256" },
                { name: "issuer",         type: "address" },
                { name: "eventTimestamp", type: "uint256" },
                { name: "blockTimestamp", type: "uint256" },
                { name: "ipfsCID",        type: "string"  },
                { name: "sha256Hash",     type: "string"  },
                { name: "metadata",        type: "string"  },
                { name: "exists",          type: "bool"    },
              ],
            },
          ],
        },
      ],
      functionName: "getEvidence",
      args: [BigInt(tokenId)],
    });

    // viem returns array; access by index and convert BigInts
    const ev = Array.isArray(evidence) ? evidence : Object.values(evidence);
    const cid = ev[4] && ev[4] !== "0" ? String(ev[4]) : null;
    const gatewayUrl = cid ? `https://gateway.pinata.cloud/ipfs/${cid}` : null;

    return res.json({
      success: true,
      tokenId: String(ev[0] ?? tokenId),
      issuer: String(ev[1] ?? ""),
      eventTimestamp: String(ev[2] ?? "0"),
      blockTimestamp: String(ev[3] ?? "0"),
      ipfsCID: cid,
      sha256Hash: String(ev[5] ?? ""),
      metadata: String(ev[6] ?? ""),
      exists: Boolean(ev[7] ?? false),
      gatewayUrl,
    });
  } catch (e) {
    console.error("[EVIDENCE] Query error:", e);
    return res.status(500).json({ success: false, error: e.message });
  }
});

/**
 * GET /api/evidence/verify/:tokenId
 * Xác thực file hash với bằng chứng trên chain
 */
app.get("/api/evidence/verify/:tokenId", async (req, res) => {
  try {
    const { tokenId } = req.params;
    const { hash } = req.query;
    if (!hash) return res.status(400).json({ success: false, error: "Missing ?hash= parameter" });

    const rpcUrl = process.env.HARDHAT_RPC_URL || "http://127.0.0.1:8545";
    const contractAddress = process.env.CONTRACT_ADDRESS;
    if (!contractAddress) {
      return res.status(400).json({ success: false, error: "CONTRACT_ADDRESS not configured" });
    }

    const { createPublicClient, http } = await import("viem");
    const { hardhat } = await import("viem/chains");

    const client = createPublicClient({
      chain: hardhat,
      transport: http(rpcUrl),
    });

    const isValid = await client.readContract({
      address: contractAddress,
      abi: [
        {
          type: "function",
          name: "verifyEvidence",
          inputs: [
            { name: "tokenId",  type: "uint256" },
            { name: "fileHash", type: "string"  },
          ],
          outputs: [{ type: "bool" }],
        },
      ],
      functionName: "verifyEvidence",
      args: [BigInt(tokenId), hash],
    });

    return res.json({ success: true, tokenId: Number(tokenId), fileHash: hash, verified: isValid });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Health check
app.get("/health", (_, r) => r.json({ status: "ok", service: "guardian-blockchain" }));

const PORT = process.env.PORT || 5001;
app.listen(PORT, () => {
  console.log(`\n=== GUARDIAN Blockchain Service ===`);
  console.log(`Listening on http://localhost:${PORT}`);
  console.log(`- POST /api/evidence/save     -> Lưu bằng chứng lên IPFS + Blockchain`);
  console.log(`- GET  /api/evidence/:tokenId -> Truy vấn bằng chứng`);
  console.log(`- GET  /api/evidence/verify   -> Xác thực hash`);
  console.log(`==================================\n`);
});
