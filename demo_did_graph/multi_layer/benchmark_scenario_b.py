# benchmark_scenario_b.py

import time
import psycopg
import statistics
import json

# ─────────────────────────────────────────────────────────
# 1) DB 연결 설정
# ─────────────────────────────────────────────────────────
conn = psycopg.connect(
    host="localhost", port=5433, dbname="edge",
    user="sam", password="dooley"
)
cur = conn.cursor()

# ─────────────────────────────────────────────────────────
# 2) 벤치마크용 쿼리 (Scenario B: DID + VC + RDB)
# ─────────────────────────────────────────────────────────
BENCH_QUERY = """
WITH RECURSIVE delegation AS (
  SELECT id AS node_id, 'HQ' AS role
    FROM hq
   WHERE id = %s
  UNION ALL
  SELECT r.child_id, r.child_type
    FROM delegation d
    JOIN delegation_relation r
      ON r.parent_id = d.node_id
)
SELECT v.vc_json
  FROM delegation del
  JOIN vc_test v
    ON v.subject_did = del.node_id
 WHERE del.role = 'Drone';
"""

# ─────────────────────────────────────────────────────────
# 3) 측정 함수
# ─────────────────────────────────────────────────────────
def benchmark(hq_id: str, iterations: int = 100):
    latencies = []
    # 워밍업
    cur.execute(BENCH_QUERY, (hq_id,))
    cur.fetchall()

    # 반복 실행
    start_all = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        cur.execute(BENCH_QUERY, (hq_id,))
        rows = cur.fetchall()
        # JSON 파싱 & 최소 검증 오버헤드 포함 (선택 사항)
        # for (vc_json,) in rows:
        #     _ = json.loads(vc_json) if isinstance(vc_json, str) else vc_json
        latencies.append(time.perf_counter() - t0)
    elapsed_all = time.perf_counter() - start_all

    # 통계 계산
    p50 = statistics.quantiles(latencies, n=100)[49]
    p95 = statistics.quantiles(latencies, n=100)[94]
    p99 = statistics.quantiles(latencies, n=100)[98]
    tps = iterations / elapsed_all

    print(f"Scenario B Benchmark (HQ = {hq_id})")
    print(f"Iterations : {iterations}")
    print(f"P50 latency : {p50*1000:.2f} ms")
    print(f"P95 latency : {p95*1000:.2f} ms")
    print(f"P99 latency : {p99*1000:.2f} ms")
    print(f"Throughput  : {tps:.2f} qps")

# ─────────────────────────────────────────────────────────
# 4) 실행
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    benchmark("HQ1", iterations=200)

    cur.close()
    conn.close()
