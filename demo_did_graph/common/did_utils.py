# common/did_utils.py

import uuid
import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_did() -> str:
    return f"did:example:{uuid.uuid4()}"

def create_vc(issuer_did: str, subject_did: str, data: dict, private_key) -> dict:
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": ["VerifiableCredential"],
        "issuer": issuer_did,
        "issuanceDate": "2024-01-01T00:00:00Z",
        "credentialSubject": {
            "id": subject_did,
            **data
        }
    }
    # 서명
    vc_bytes = json.dumps(vc, sort_keys=True).encode("utf-8")
    signature = private_key.sign(vc_bytes)
    vc["proof"] = {
        "type": "Ed25519Signature2020",
        "created": "2024-01-01T00:00:00Z",
        "verificationMethod": f"{issuer_did}#key-1",
        "proofPurpose": "assertionMethod",
        "signatureValue": signature.hex()
    }
    return vc

def verify_vc(vc: dict, public_key) -> bool:
    proof = vc.get("proof")
    if not proof:
        return False
    signature = bytes.fromhex(proof.get("signatureValue"))
    data_copy = vc.copy()
    del data_copy["proof"]
    vc_bytes = json.dumps(data_copy, sort_keys=True).encode("utf-8")
    try:
        public_key.verify(signature, vc_bytes)
        return True
    except Exception:
        return False


# ----------------------------
# 키 생성 및 파일 저장/로드
# ----------------------------

def generate_key_pair():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def save_private_key(private_key, filename: str):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(filename, 'wb') as f:
        f.write(pem)


def save_public_key(public_key, filename: str):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(filename, 'wb') as f:
        f.write(pem)


def load_private_key(filename: str):
    with open(filename, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(filename: str):
    with open(filename, 'rb') as f:
        return serialization.load_pem_public_key(f.read())