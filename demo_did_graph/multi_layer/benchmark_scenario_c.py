# benchmark_scenario_c.py

import time
import psycopg
import statistics

# ─────────────────────────────────────────────────────────
# 1) DB 연결
# ─────────────────────────────────────────────────────────
conn = psycopg.connect(
    host="localhost", port=5433, dbname="edge",
    user="sam", password="dooley"
)
cur = conn.cursor()

# ─────────────────────────────────────────────────────────
# 2) Graph 경로 설정
# ─────────────────────────────────────────────────────────
cur.execute("SET graph_path = vc_graph;")

# ─────────────────────────────────────────────────────────
# 4) 측정 함수
# ─────────────────────────────────────────────────────────
def benchmark(hq_id, iterations=100):
    latencies = []
    query = f"""
    MATCH (hq:HQ {{id: '{hq_id}'}})
      -[:DELEGATES*1..4]->(d:Drone)
      <-[:ASSERTS]-(v:VC)
    RETURN v.vc_json;
    """
    # 워밍업
    cur.execute(query); cur.fetchall()

    start_all = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        cur.execute(query); cur.fetchall()
        latencies.append(time.perf_counter() - t0)
    elapsed_all = time.perf_counter() - start_all

    # 통계 계산
    p50 = statistics.quantiles(latencies, n=100)[49]
    p95 = statistics.quantiles(latencies, n=100)[94]
    p99 = statistics.quantiles(latencies, n=100)[98]
    tps = iterations / elapsed_all

    print(f"Scenario C Benchmark (HQ = {hq_id})")
    print(f"Iterations  : {iterations}")
    print(f"P50 latency : {p50*1000:.2f} ms")
    print(f"P95 latency : {p95*1000:.2f} ms")
    print(f"P99 latency : {p99*1000:.2f} ms")
    print(f"Throughput  : {tps:.2f} qps")

# ─────────────────────────────────────────────────────────
# 5) 스크립트 실행
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    benchmark("HQ1", iterations=200)
    cur.close()
    conn.close()
