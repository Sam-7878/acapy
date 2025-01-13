import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives import serialization

# 1. 자격 증명 데이터 준비
verifiable_credential = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "id": "http://example.edu/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {
        "id": "did:example:123456789abcdefghi",
        "name": "Example University"
    },
    "credentialSubject": {
        "id": "did:example:abcdef1234567",
        "degree": {
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts"
        }
    },
    "issuanceDate": "2025-01-13T21:19:10Z"
}

# 2. 키 생성
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# 3. 서명 생성
def sign_vc(private_key, vc):
    serialized_vc = json.dumps(vc, sort_keys=True).encode("utf-8")
    signature = private_key.sign(
        serialized_vc,
        ec.ECDSA(hashes.SHA256())
    )
    return base64.urlsafe_b64encode(signature).decode("utf-8")

# 4. Self-contained Verifiable Credential 생성
verifiable_credential["proof"] = {
    "type": "EcdsaSecp256r1Signature2019",
    "created": "2025-01-13T21:19:10Z",
    "verificationMethod": {
        "id": "did:example:123456789abcdefghi#keys-1",
        "type": "EcdsaSecp256r1",
        "publicKeyPem": public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8"),
    },
    "signature": sign_vc(private_key, verifiable_credential)
}

# 5. 자격 증명 저장
with open("self_contained_vc.json", "w") as f:
    json.dump(verifiable_credential, f, indent=4)

print("Self-contained Verifiable Credential 생성 완료: self_contained_vc.json")
