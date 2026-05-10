const hre = require("hardhat");

async function main() {
  await hre.run("compile");
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const EvidenceNFT = await hre.ethers.getContractFactory("EvidenceNFT");
  const contract = await EvidenceNFT.deploy();

  await contract.waitForDeployment();
  const address = await contract.getAddress();

  console.log("EvidenceNFT deployed at:", address);

  const fs = require("fs");
  const path = require("path");
  const envPath = path.join(__dirname, "..", "..", ".env");
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
    console.log("Set CONTRACT_ADDRESS=" + address);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
