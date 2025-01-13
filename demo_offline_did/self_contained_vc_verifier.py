import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# 1. Self-contained Verifiable Credential 로드
with open("self_contained_vc.json", "r") as f:
    verifiable_credential = json.load(f)

# 2. 서명 및 공개 키 가져오기
proof = verifiable_credential["proof"]
signature = base64.urlsafe_b64decode(proof["signature"])
public_key_pem = proof["verificationMethod"]["publicKeyPem"]

# 3. 공개 키 로드
public_key = load_pem_public_key(public_key_pem.encode("utf-8"))

# 4. 서명 검증 함수
def verify_signature(public_key, vc, signature):
    # Proof 데이터를 제외한 Verifiable Credential 직렬화
    vc_copy = vc.copy()
    del vc_copy["proof"]

    serialized_vc = json.dumps(vc_copy, sort_keys=True).encode("utf-8")
    try:
        public_key.verify(
            signature,
            serialized_vc,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except Exception as e:
        print("서명 검증 실패:", e)
        return False

# 5. 검증 실행
is_valid = verify_signature(public_key, verifiable_credential, signature)

if is_valid:
    print("Self-contained Verifiable Credential 검증 성공!")
else:
    print("Self-contained Verifiable Credential 검증 실패!")
