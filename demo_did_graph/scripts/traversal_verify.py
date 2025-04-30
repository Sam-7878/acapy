# scripts/traversal_verify.py

import time
import psycopg
import json

from pathlib import Path
import sys, os
sys.path.append(str(Path(__file__).resolve().parent.parent))
# === 모듈 임포트 ===
from common.load_config import TestConfig
from common.sign_verify import verify_signature, load_public_key
from common.did_utils import verify_vc

# === Traversal 검증: 시나리오 A ===
def verify_traversal_a(config: TestConfig) -> dict:
    conn = psycopg.connect(
        host=config.db_host,
        port=config.db_port,
        dbname=config.db_name,
        user=config.db_user,
        password=config.db_password
    )
    cur = conn.cursor()

    pub_key = load_public_key("common/keys/commander_public.pem")

    start = time.perf_counter()
    cur.execute("SELECT payload, signature FROM mission_test;")
    rows = cur.fetchall()

    verified = sum(
        1 for payload, sig in rows if verify_signature(pub_key, sig, payload)
    )

    elapsed = time.perf_counter() - start
    cur.close()
    conn.close()

    return {"verified": verified, "elapsed": elapsed}


# === Traversal 검증: 시나리오 B ===
def verify_traversal_b(config: TestConfig) -> dict:
    conn = psycopg.connect(
        host=config.db_host,
        port=config.db_port,
        dbname=config.db_name,
        user=config.db_user,
        password=config.db_password
    )
    cur = conn.cursor()

    issuer_pub = load_public_key("common/keys/commander_public.pem")

    start = time.perf_counter()
    cur.execute("SELECT vc_json FROM vc_test;")
    rows = cur.fetchall()

    verified = sum(
#        1 for (vc_json,) in rows if verify_vc(vc=json.loads(vc_json), public_key=issuer_pub)
        1 for (vc_json,) in rows if verify_vc(vc=vc_json, public_key=issuer_pub)
    )

    elapsed = time.perf_counter() - start
    cur.close()
    conn.close()

    return {"verified": verified, "elapsed": elapsed}


# === Traversal 검증: 시나리오 C ===
def verify_traversal_c(config: TestConfig) -> dict:
    conn = psycopg.connect(
        host=config.db_host,
        port=config.db_port,
        dbname=config.db_name,
        user=config.db_user,
        password=config.db_password
    )
    cur = conn.cursor()

    cur.execute("SET graph_path = vc_graph;")
    issuer_pub = load_public_key("common/keys/commander_public.pem")

    start = time.perf_counter()
    cur.execute("MATCH (v:VC) RETURN v.vc_json;")
    rows = cur.fetchall()

    verified = sum(
        1 for (vc_json,) in rows if verify_vc(vc=json.loads(vc_json), public_key=issuer_pub)
    )

    elapsed = time.perf_counter() - start
    cur.close()
    conn.close()

    return {"verified": verified, "elapsed": elapsed}

# === 엔트리 포인트 ===
if __name__ == "__main__":
    cfg = TestConfig("config/test_small.json")
#    cfg = TestConfig("config/test_large.json")
    result_a = verify_traversal_a(cfg)
    result_b = verify_traversal_b(cfg)
    result_c = verify_traversal_c(cfg)

    print("[Verify A]", result_a)
    print("[Verify B]", result_b)
    print("[Verify C]", result_c)
