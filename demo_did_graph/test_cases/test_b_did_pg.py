# testcases/test_b_did_pg.py

import time
import psycopg
import json
import random

from pathlib import Path
import sys, os
sys.path.append(str(Path(__file__).resolve().parent.parent))
# === 모듈 임포트 ===
from common.load_config import TestConfig
from common.did_utils import generate_did, generate_key_pair, create_vc, verify_vc


def run_test_case_b(config: TestConfig):
    print("[B-Test] Running DID + VC + PostgreSQL Test")

    # Seed 고정 (재현 가능성 확보)
    random.seed(config.random_seed)

    # DB 연결
    conn = psycopg.connect(
        host=config.db_host,
        port=config.db_port,
        dbname=config.db_name,
        user=config.db_user,
        password=config.db_password
    )
    cur = conn.cursor()

    # 테스트 테이블 초기화
    cur.execute("DROP TABLE IF EXISTS vc_test;")
    cur.execute("""
        CREATE TABLE vc_test (
            vc_id TEXT PRIMARY KEY,
            issuer_did TEXT,
            subject_did TEXT,
            vc_json JSONB
        );
    """)
    conn.commit()

    # 키 쌍 생성 (명령자 역할)
    issuer_private, issuer_public = generate_key_pair()

    insert_start = time.perf_counter()

    # VC 생성 및 삽입
    for i in range(config.num_mission):
        issuer_did = generate_did()
        subject_did = generate_did()
        payload = {
            "mission_id": f"M{i:04}",
            "content": f"Mission content {i}"
        }

        vc = create_vc(issuer_did, subject_did, payload, issuer_private)
        vc_id = vc["id"]

        cur.execute(
            "INSERT INTO vc_test (vc_id, issuer_did, subject_did, vc_json) VALUES (%s, %s, %s, %s)",
            (vc_id, issuer_did, subject_did, json.dumps(vc))
        )

    conn.commit()
    insert_time = time.perf_counter() - insert_start

    print(f"[B-Test] Inserted {config.num_mission} VCs in {insert_time:.4f} seconds")

    # VC 검증 테스트
    verify_start = time.perf_counter()
    cur.execute("SELECT vc_json FROM vc_test")
    rows = cur.fetchall()

    verified_count = 0
    for row in rows:
        vc = row[0]
        if verify_vc(vc, issuer_public):
            verified_count += 1

    verify_time = time.perf_counter() - verify_start
    print(f"[B-Test] Verified {verified_count} VCs in {verify_time:.4f} seconds")

    cur.close()
    conn.close()

    return {
        "insert_time": insert_time,
        "verify_time": verify_time,
        "total": config.num_mission
    }

if __name__ == "__main__":
    cfg = TestConfig("config/test_small.json")
    result = run_test_case_b(cfg)
    print("[B-Test] Result:", result)
