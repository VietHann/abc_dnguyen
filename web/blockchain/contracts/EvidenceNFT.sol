// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EvidenceNFT
 * @notice Lưu trữ bằng chứng bạo lực học đường bất biến trên blockchain.
 * Mỗi bằng chứng là một NFT chứa: CID IPFS, hash SHA-256, timestamp, metadata sự kiện.
 * Không thể sửa đổi hay xoá sau khi mint.
 */
contract EvidenceNFT {
    // Struct lưu thông tin bằng chứng
    struct Evidence {
        uint256 tokenId;
        address issuer;           // người tạo bằng chứng (hệ thống)
        uint256 eventTimestamp;   // thời điểm sự kiện xảy ra
        uint256 blockTimestamp;    // thời điểm mint lên chain
        string  ipfsCID;          // CID của file gốc trên IPFS
        string  sha256Hash;        // SHA-256 hash của file gốc
        string  metadata;          // JSON metadata (json encoded): class, confidence, location...
        bool    exists;
    }

    // Mapping tokenId -> Evidence
    mapping(uint256 => Evidence) public evidenceRegistry;

    // Mapping tokenId -> holder (dùng cho ERC-721 compliance)
    mapping(uint256 => address) public tokenOwner;

    // Tổng số token đã mint
    uint256 public totalEvidence;

    // Sự kiện
    event EvidenceMinted(
        uint256 indexed tokenId,
        address indexed issuer,
        uint256 eventTimestamp,
        string  ipfsCID,
        string  sha256Hash
    );

    // Modifier kiểm tra evidence tồn tại
    modifier evidenceExists(uint256 tokenId) {
        require(evidenceRegistry[tokenId].exists, "Evidence does not exist");
        _;
    }

    /**
     * @notice Mint một bằng chứng bất biến lên blockchain
     * @param eventTimestamp Thời điểm sự kiện xảy ra (Unix timestamp)
     * @param ipfsCID       CID của file trên IPFS
     * @param sha256Hash    SHA-256 hash của file gốc
     * @param metadata      JSON string chứa class, confidence, bbox...
     * @return tokenId      ID của NFT vừa được mint
     */
    function mintEvidence(
        uint256 eventTimestamp,
        string calldata ipfsCID,
        string calldata sha256Hash,
        string calldata metadata
    ) external returns (uint256 tokenId) {
        require(bytes(ipfsCID).length > 0,   "IPFS CID cannot be empty");
        require(bytes(sha256Hash).length > 0, "SHA256 hash cannot be empty");

        totalEvidence += 1;
        tokenId = totalEvidence;
        uint256 blockTs = block.timestamp;

        evidenceRegistry[tokenId] = Evidence({
            tokenId:        tokenId,
            issuer:         msg.sender,
            eventTimestamp: eventTimestamp,
            blockTimestamp: blockTs,
            ipfsCID:        ipfsCID,
            sha256Hash:     sha256Hash,
            metadata:       metadata,
            exists:         true
        });

        tokenOwner[tokenId] = msg.sender;

        emit EvidenceMinted(tokenId, msg.sender, eventTimestamp, ipfsCID, sha256Hash);
    }

    /**
     * @notice Lấy thông tin bằng chứng theo tokenId
     */
    function getEvidence(uint256 tokenId) external view evidenceExists(tokenId) returns (Evidence memory) {
        return evidenceRegistry[tokenId];
    }

    /**
     * @notice Xác thực file có khớp với bằng chứng đã lưu không
     * @param tokenId   ID bằng chứng
     * @param fileHash  SHA-256 hash cần kiểm tra
     * @return bool     True nếu hash khớp
     */
    function verifyEvidence(uint256 tokenId, string calldata fileHash)
        external
        view
        evidenceExists(tokenId)
        returns (bool)
    {
        return keccak256(abi.encodePacked(evidenceRegistry[tokenId].sha256Hash)) ==
               keccak256(abi.encodePacked(fileHash));
    }

    /**
     * @notice Lấy owner của token
     */
    function ownerOf(uint256 tokenId) external view evidenceExists(tokenId) returns (address) {
        return tokenOwner[tokenId];
    }
}
