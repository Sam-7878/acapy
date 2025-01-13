import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

# 1. DID 문서와 인증서 준비
did_document = {
    "@context": "https://w3id.org/did/v1",
    "id": "did:example:123456789abcdefghi",
    "verificationMethod": [{
        "id": "did:example:123456789abcdefghi#keys-1",
        "type": "Ed25519VerificationKey2018",
        "controller": "did:example:123456789abcdefghi",
        "publicKeyBase58": "2jKdmc..."
    }]
}

verifiable_credential = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "id": "http://example.edu/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": "did:example:123456789abcdefghi",
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

# 3. 데이터 패키징
combined_package = {
    "did_document": did_document,
    "verifiable_credential": verifiable_credential
}

# 4. 서명 생성
def sign_data(private_key, data):
    serialized_data = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = private_key.sign(
        serialized_data,
        ec.ECDSA(hashes.SHA256())
    )
    return base64.urlsafe_b64encode(signature).decode('utf-8')

combined_package['signature'] = sign_data(private_key, combined_package)

# 5. 공개 키 저장
public_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('packaging_with_did.json', 'w') as f:
    json.dump(combined_package, f, indent=4)

with open('public_key.pem', 'wb') as f:
    f.write(public_key_bytes)

print("오프라인 DID 패키지 생성 완료: packaging_with_did.json")
print("공개 키 저장 완료: public_key.pem")
