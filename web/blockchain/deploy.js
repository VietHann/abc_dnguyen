import { task } from "hardhat/config";

task("deploy", "Deploy EvidenceNFT contract").setAction(async (_, hre) => {
  const { deploy } = hre.deployments;
  const accounts = await hre.getUnnamedAccounts();

  const result = await deploy("EvidenceNFT", {
    from: accounts[0],
    args: [],
    log: true,
  });

  console.log(`Contract deployed at: ${result.address}`);
  console.log(`Run: cp .env.example .env && echo CONTRACT_ADDRESS=${result.address} >> .env`);
});
