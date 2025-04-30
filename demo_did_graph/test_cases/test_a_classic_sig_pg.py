# testcases/test_a_classic_sig_pg.py

import time
import random
from pathlib import Path
import psycopg
import sys, os
sys.path.append(str(Path(__file__).resolve().parent.parent))
# === 모듈 임포트 ===
from common.load_config import TestConfig
from common.sign_verify import sign_data, verify_signature, load_private_key, load_public_key

# === 설정 ===
PRIVATE_KEY_PATH = "common/keys/commander_private.pem"
PUBLIC_KEY_PATH = "common/keys/commander_public.pem"

# === 테스트 함수 ===
def run_test_case_a(config: TestConfig):
    print("[A-Test] Running Classic Signature + PostgreSQL Test")

    # 키 로드
    priv_key = load_private_key(PRIVATE_KEY_PATH)
    pub_key = load_public_key(PUBLIC_KEY_PATH)

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
    cur.execute("DROP TABLE IF EXISTS mission_test;")
    cur.execute("""
        CREATE TABLE mission_test (
            mission_id TEXT PRIMARY KEY,
            payload TEXT,
            signature BYTEA
        );
    """)
    conn.commit()

    # 노드 수만큼 명령 생성 및 서명 삽입
    start_time = time.perf_counter()

    for i in range(config.num_mission):
        mission_id = f"M{i:04}"
        payload = f"Mission payload {i}"
        signature = sign_data(priv_key, payload)

        cur.execute(
            "INSERT INTO mission_test (mission_id, payload, signature) VALUES (%s, %s, %s)",
            (mission_id, payload, signature)
        )

    conn.commit()
    insert_time = time.perf_counter() - start_time

    print(f"[A-Test] Inserted {config.num_mission} missions in {insert_time:.4f} seconds")

    # 검증 테스트
    verify_start = time.perf_counter()
    cur.execute("SELECT mission_id, payload, signature FROM mission_test")
    rows = cur.fetchall()

    verified_count = 0
    for row in rows:
        mission_id, payload, signature = row
        if verify_signature(pub_key, signature, payload):
            verified_count += 1

    verify_time = time.perf_counter() - verify_start

    print(f"[A-Test] Verified {verified_count} missions in {verify_time:.4f} seconds")

    # 종료
    cur.close()
    conn.close()

    return {
        "insert_time": insert_time,
        "verify_time": verify_time,
        "total": config.num_mission
    }

# 단독 실행 테스트
if __name__ == "__main__":
#    cfg = TestConfig("config/test_small.json")
    cfg = TestConfig("config/test_large.json")
    result = run_test_case_a(cfg)
    print("[A-Test] Result:", result)
