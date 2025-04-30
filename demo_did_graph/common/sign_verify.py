# sign_verify.py

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def load_private_key(filename):
    with open(filename, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def load_public_key(filename):
    with open(filename, 'rb') as f:
        return serialization.load_pem_public_key(f.read())

def sign_data(private_key, data: str) -> bytes:
    signature = private_key.sign(data.encode('utf-8'))
    return signature

def verify_signature(public_key, signature: bytes, data: str) -> bool:
    try:
        public_key.verify(signature, data.encode('utf-8'))
        return True
    except Exception:
        return False

if __name__ == "__main__":
    # Example usage
    commander_private = load_private_key("common/keys/commander_private.pem")
    commander_public = load_public_key("common/keys/commander_public.pem")

    message = "Test Mission Data"
    signature = sign_data(commander_private, message)

    result = verify_signature(commander_public, signature, message)
    print("Signature valid:", result)
