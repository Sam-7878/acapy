import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# 1. 패키지 로드
with open('packaging_with_did.json', 'r') as f:
    received_package = json.load(f)

# 2. 공개 키 로드
with open('public_key.pem', 'rb') as f:
    public_key = load_pem_public_key(f.read())

# 3. 서명 검증
def verify_signature(public_key, data, signature):
    serialized_data = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = base64.urlsafe_b64decode(signature)
    try:
        public_key.verify(
            signature,
            serialized_data,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except Exception as e:
        print("서명 검증 실패:", e)
        return False

# 검증 실행
data_to_verify = {
    "did_document": received_package['did_document'],
    "verifiable_credential": received_package['verifiable_credential']
}

is_valid = verify_signature(public_key, data_to_verify, received_package['signature'])

if is_valid:
    print("패키지 검증 성공!")
else:
    print("패키지 검증 실패!")
