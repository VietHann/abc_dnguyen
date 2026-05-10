/**
 * Deploy EvidenceNFT contract to Hardhat local node using viem
 */
import { createPublicClient, createWalletClient, http } from "viem";
import { hardhat } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PRIVATE_KEY = process.env.PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

const contractAbi = [
  {
    type: "constructor",
    inputs: [],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "evidenceRegistry",
    inputs: [{ name: "tokenId", type: "uint256" }],
    outputs: [
      {
        components: [
          { name: "tokenId",        type: "uint256" },
          { name: "issuer",        type: "address" },
          { name: "eventTimestamp", type: "uint256" },
          { name: "blockTimestamp",type: "uint256" },
          { name: "ipfsCID",       type: "string"  },
          { name: "sha256Hash",    type: "string"  },
          { name: "metadata",      type: "string"  },
          { name: "exists",        type: "bool"    },
        ],
        name: "",
        type: "tuple",
      },
    ],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "totalEvidence",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "mintEvidence",
    inputs: [
      { name: "eventTimestamp", type: "uint256" },
      { name: "ipfsCID",       type: "string"  },
      { name: "sha256Hash",   type: "string"  },
      { name: "metadata",      type: "string"  },
    ],
    outputs: [{ name: "tokenId", type: "uint256" }],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "getEvidence",
    inputs: [{ name: "tokenId", type: "uint256" }],
    outputs: [
      {
        components: [
          { name: "tokenId",        type: "uint256" },
          { name: "issuer",        type: "address" },
          { name: "eventTimestamp", type: "uint256" },
          { name: "blockTimestamp",type: "uint256" },
          { name: "ipfsCID",       type: "string"  },
          { name: "sha256Hash",    type: "string"  },
          { name: "metadata",      type: "string"  },
          { name: "exists",        type: "bool"    },
        ],
        name: "",
        type: "tuple",
      },
    ],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "verifyEvidence",
    inputs: [
      { name: "tokenId",  type: "uint256" },
      { name: "fileHash", type: "string"  },
    ],
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "ownerOf",
    inputs: [{ name: "tokenId", type: "uint256" }],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "event",
    name: "EvidenceMinted",
    inputs: [
      { name: "tokenId",        type: "uint256", indexed: true },
      { name: "issuer",        type: "address",  indexed: true },
      { name: "eventTimestamp",type: "uint256"            },
      { name: "ipfsCID",       type: "string"             },
      { name: "sha256Hash",   type: "string"             },
    ],
    anonymous: false,
  },
];

async function main() {
  // 1. Read compiled artifact
  const artifactPath = path.join(__dirname, "..", "artifacts", "contracts", "EvidenceNFT.sol", "EvidenceNFT.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  console.log("Contract artifact loaded. Bytecode length:", artifact.bytecode.length);

  // 2. Create wallet client with Hardhat account #0
  const account = privateKeyToAccount(PRIVATE_KEY);
  console.log("Deploying from:", account.address);

  const walletClient = createWalletClient({
    account,
    chain: hardhat,
    transport: http("http://127.0.0.1:8545"),
  });

  const publicClient = createPublicClient({
    chain: hardhat,
    transport: http("http://127.0.0.1:8545"),
  });

  // 3. Deploy
  console.log("Deploying EvidenceNFT...");
  const hash = await walletClient.deployContract({
    abi: contractAbi,
    bytecode: artifact.bytecode,
    args: [],
  });

  console.log("Transaction hash:", hash);
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  const address = receipt.contractAddress;

  console.log("\n========================================");
  console.log("EvidenceNFT deployed at:", address);
  console.log("Block number:", receipt.blockNumber);
  console.log("========================================\n");

  // 4. Update .env
  const envPath = path.join(__dirname, "..", ".env");
  try {
    let envContent = fs.readFileSync(envPath, "utf8");
    const lines = envContent.split("\n").map(line => {
      if (line.startsWith("CONTRACT_ADDRESS=")) {
        return `CONTRACT_ADDRESS=${address}`;
      }
      return line;
    });
    fs.writeFileSync(envPath, lines.join("\n"));
    console.log("Updated .env with CONTRACT_ADDRESS");
  } catch (e) {
    console.log("Could not update .env manually set:");
    console.log("  CONTRACT_ADDRESS=" + address);
  }

  // 5. Quick test mint
  console.log("\nTesting mintEvidence...");
  const testHash = await walletClient.writeContract({
    address,
    abi: contractAbi,
    functionName: "mintEvidence",
    args: [
      BigInt(Math.floor(Date.now() / 1000)),
      "QmTestCID123456789",
      "a1b2c3d4e5f6",
      JSON.stringify({ test: true, class: "violence", confidence: 0.95 }),
    ],
  });
  const testReceipt = await publicClient.waitForTransactionReceipt({ hash: testHash });
  console.log("Test mint tx:", testHash);
  console.log("Block:", testReceipt.blockNumber);

  const total = await publicClient.readContract({
    address,
    abi: contractAbi,
    functionName: "totalEvidence",
  });
  console.log("Total evidence on chain:", Number(total));

  console.log("\nDeploy and test complete!");
}

main().catch((e) => {
  console.error("Error:", e);
  process.exit(1);
});
