# setup_scenario_a.py

import time
from pathlib import Path
import psycopg
from psycopg import sql, Binary
import random
import sys, os

# ────────────────────────────────────────────────────────
# 1) 프로젝트 루트를 PYTHONPATH에 추가 (common 모듈 로드용)
# ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from common.load_config import TestConfig
from common.sign_verify import load_private_key, sign_data

# ────────────────────────────────────────────────────────
# 2) 설정 파라미터
# ────────────────────────────────────────────────────────
CONFIG_PATH       = "config/test_small.json"  # 또는 test_large.json
HQ_ID             = "HQ1"
REGIONAL_COUNT    = 100
UNIT_COUNT        = 200
SQUAD_COUNT       = 500
DRONES_PER_SQUAD  = 5

# ────────────────────────────────────────────────────────
# 3) DB 연결
# ────────────────────────────────────────────────────────
cfg = TestConfig(CONFIG_PATH)
conn = psycopg.connect(
    host=cfg.db_host,
    port=cfg.db_port,
    dbname=cfg.db_name,
    user=cfg.db_user,
    password=cfg.db_password
)
cur = conn.cursor()

# ────────────────────────────────────────────────────────
# 4) 스키마 초기화
# ────────────────────────────────────────────────────────
cur.execute("DROP TABLE IF EXISTS mission_test;")
cur.execute("DROP TABLE IF EXISTS delegation_relation;")
cur.execute("DROP TABLE IF EXISTS hq;")
conn.commit()

cur.execute("""
CREATE TABLE hq (
  id TEXT PRIMARY KEY
);
""")
cur.execute("""
CREATE TABLE delegation_relation (
  parent_id  TEXT NOT NULL,
  child_id   TEXT NOT NULL,
  child_type TEXT NOT NULL,
  PRIMARY KEY(parent_id, child_id)
);
""")
cur.execute("""
CREATE TABLE mission_test (
  mission_id TEXT PRIMARY KEY,
  drone_id   TEXT NOT NULL,
  cid        TEXT NOT NULL,       -- 발행자 ID (여기서는 HQ)
  payload    TEXT NOT NULL,
  signature  BYTEA    NOT NULL
);
""")
conn.commit()

# ────────────────────────────────────────────────────────
# 5) 계층 노드 생성
# ────────────────────────────────────────────────────────
start = time.perf_counter()

# 5.1 HQ 삽입
cur.execute(
    "INSERT INTO hq (id) VALUES (%s) ON CONFLICT DO NOTHING;",
    (HQ_ID,)
)

# 5.2 RegionalCmd 삽입 & 관계
regionals = [f"R{i:03d}" for i in range(1, REGIONAL_COUNT+1)]
for rid in regionals:
    cur.execute(
        "INSERT INTO delegation_relation (parent_id, child_id, child_type) VALUES (%s, %s, %s)",
        (HQ_ID, rid, "Regional")
    )

# 5.3 UnitCmd 삽입 & 관계
units = [f"U{i:04d}" for i in range(1, UNIT_COUNT+1)]
for idx, uid in enumerate(units):
    parent = regionals[idx % REGIONAL_COUNT]
    cur.execute(
        "INSERT INTO delegation_relation (parent_id, child_id, child_type) VALUES (%s, %s, %s)",
        (parent, uid, "Unit")
    )

# 5.4 Squad 삽입 & 관계
squads = [f"S{i:05d}" for i in range(1, SQUAD_COUNT+1)]
for idx, sid in enumerate(squads):
    parent = units[idx % UNIT_COUNT]
    cur.execute(
        "INSERT INTO delegation_relation (parent_id, child_id, child_type) VALUES (%s, %s, %s)",
        (parent, sid, "Squad")
    )

# 5.5 Drone 삽입 & 관계
drones = []
for idx, sid in enumerate(squads):
    for j in range(1, DRONES_PER_SQUAD+1):
        did = f"D{idx:05d}_{j:02d}"
        drones.append(did)
        cur.execute(
            "INSERT INTO delegation_relation (parent_id, child_id, child_type) VALUES (%s, %s, %s)",
            (sid, did, "Drone")
        )

conn.commit()
print(f"› 계층 생성 완료: {len(regionals)} Regionals, {len(units)} Units, {len(squads)} Squads, {len(drones)} Drones")

# ────────────────────────────────────────────────────────
# 6) 미션 생성 및 서명 삽입
# ────────────────────────────────────────────────────────
priv_key = load_private_key("common/keys/commander_private.pem")
inserted = 0

for idx, drone_id in enumerate(drones):
    mission_id = f"M{idx:06d}"
    payload    = f"Payload for mission {mission_id}"
    signature  = sign_data(priv_key, payload)
    cur.execute("""
        INSERT INTO mission_test (mission_id, drone_id, cid, payload, signature)
        VALUES (%s, %s, %s, %s, %s)
    """, (mission_id, drone_id, HQ_ID, payload, Binary(signature)))
    inserted += 1

conn.commit()
elapsed = time.perf_counter() - start
print(f"› 미션 생성 및 서명 완료: {inserted}건 ({elapsed:.2f}s)")

# ────────────────────────────────────────────────────────
# 7) 정리
# ────────────────────────────────────────────────────────
cur.close()
conn.close()
print("Environment setup for Scenario A is complete.")
