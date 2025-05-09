#!/usr/bin/env python3
# benchmark_scenario_c.py
# Scenario C Dynamic Topology Benchmark: DID + VC + AgensGraph

import time
import psycopg
import statistics
import json
import random
import argparse
import csv
from pathlib import Path
import sys, os

# 프로젝트 루트를 PYTHONPATH에 추가 (common 모듈 로드용)
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from common.load_config import TestConfig
from common.bench_utils import benchmark_query


# ─────────────────────────────────────────────────────────
# 1) Cypher 쿼리 생성 함수
# ─────────────────────────────────────────────────────────
def get_bench_query(hq_id: str, max_depth: int) -> str:
    return f"""
MATCH (hq:HQ {{id:'{hq_id}'}})
      -[:DELEGATES*1..{max_depth}]->(d:Drone)
      <-[:ASSERTS]-(v:VC)
RETURN count(v) AS vc_count;
"""

# ─────────────────────────────────────────────────────────
# 2) 벤치마크 실행 함수
# ─────────────────────────────────────────────────────────
# def benchmark_query(cur, query: str, iterations: int):
#     latencies = []
#     # 워밍업
#     cur.execute(query)
#     cur.fetchone()

#     # 반복 실행
#     start_all = time.perf_counter()
#     for _ in range(iterations):
#         t0 = time.perf_counter()
#         cur.execute(query)
#         _ = cur.fetchone()[0]
#         latencies.append(time.perf_counter() - t0)
#     elapsed_all = time.perf_counter() - start_all

#     # 통계 계산
#     p50 = statistics.quantiles(latencies, n=100)[49]
#     p95 = statistics.quantiles(latencies, n=100)[94]
#     p99 = statistics.quantiles(latencies, n=100)[98]
#     tps = iterations / elapsed_all
#     return p50, p95, p99, tps

# ─────────────────────────────────────────────────────────
# 3) Scenario별 워크로드 함수
# ─────────────────────────────────────────────────────────
def scenario1_realtime_turntaking(cur, conn, cfg, params, nodes, depths, iterations, rows, drones_list):
    interval = params['turn_taking']['interval_sec']
    ratio = params['turn_taking']['update_ratio']
    for total in nodes:
        print(f"\n-- Scale-up: {total} nodes (Turn-Taking) --")
        for depth in depths:
            update_count = int(cfg.num_drones * ratio)
            selected = random.sample(drones_list, update_count)
            # 위임 업데이트: 기존 DELEGATES 엣지 삭제 후 재생성
            for did in selected:
                cur.execute(
                    f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;"
                )
                cur.execute(
                    f"MATCH (hq:HQ {{id:'{cfg.headquarters_id}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);"
                )
            conn.commit()
            time.sleep(interval)
            query = get_bench_query(cfg.headquarters_id, depth)
            p50, p95, p99, tps = benchmark_query(cur, query, iterations)
            print(f"Depth {depth} → P50: {p50*1000:.2f} ms, P95: {p95*1000:.2f} ms, P99: {p99*1000:.2f} ms, TPS: {tps:.2f}")
            rows.append({
                'scenario': 'C-1',
                'scale_up': total,
                'depth': depth,
                'p50_ms': p50*1000,
                'p95_ms': p95*1000,
                'p99_ms': p99*1000,
                'tps': tps
            })


def scenario2_chain_churn(cur, conn, cfg, params, nodes, depths, iterations, rows, drones_list):
    cycle = params['chain_churn']['depth_cycle']
    interval = params['chain_churn']['cycle_interval_sec']
    ratio = params['chain_churn']['update_ratio']
    for depth in cycle:
        print(f"\n-- Chain-Churn: depth={depth} --")
        update_count = int(cfg.num_drones * ratio)
        selected = random.sample(drones_list, update_count)
        for did in selected:
            cur.execute(
                f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;"
            )
            cur.execute(
                f"MATCH (hq:HQ {{id:'{cfg.headquarters_id}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);"
            )
        conn.commit()
        time.sleep(interval)
        query = get_bench_query(cfg.headquarters_id, depth)
        p50, p95, p99, tps = benchmark_query(cur, query, iterations)
        print(f"Depth {depth} → P50: {p50*1000:.2f} ms, P95: {p95*1000:.2f} ms, P99: {p99*1000:.2f} ms, TPS: {tps:.2f}")
        rows.append({
            'scenario': 'C-2',
            'scale_up': '',
            'depth': depth,
            'p50_ms': p50*1000,
            'p95_ms': p95*1000,
            'p99_ms': p99*1000,
            'tps': tps
        })


def scenario3_partition_reconciliation(cur, conn, cfg, params, nodes, depths, iterations, rows, drones_list):
    split = params['partition_reconciliation']['split_ratio']
    split_duration = params['partition_reconciliation']['split_duration_sec']
    recon_sync = params['partition_reconciliation']['post_reconcile_sync_requests']
    total = cfg.num_drones
    boundary = int(total * split[0])
    print(f"\n-- Partition: A={boundary}, B={total-boundary}, duration={split_duration}s --")
    start = time.time()
    # Partition 동안 계속 업데이트
    while time.time() - start < split_duration:
        for did in drones_list[:boundary]:
            cur.execute(
                f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;"
            )
            cur.execute(
                f"MATCH (hq:HQ {{id:'{cfg.headquarters_id}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);"
            )
        for did in drones_list[boundary:]:
            cur.execute(
                f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;"
            )
            cur.execute(
                f"MATCH (hq:HQ {{id:'{cfg.headquarters_id}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);"
            )
        conn.commit()
    # 재결합 벤치마크
    print(f"Partition 해제, 동기화 {recon_sync}건 --")
    query = get_bench_query(cfg.headquarters_id, depths[0])
    p50, p95, p99, tps = benchmark_query(cur, query, recon_sync)
    print(f"Reconciliation → P50: {p50*1000:.2f} ms, P95: {p95*1000:.2f} ms, P99: {p99*1000:.2f} ms, TPS: {tps:.2f}")
    rows.append({
        'scenario': 'C-3',
        'scale_up': total,
        'depth': depths[0],
        'p50_ms': p50*1000,
        'p95_ms': p95*1000,
        'p99_ms': p99*1000,
        'tps': tps
    })

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scenario C Dynamic Topology Benchmark")
    parser.add_argument('-c', '--config', required=True, help='Path to config JSON')
    parser.add_argument('-s', '--scenario', required=True, choices=['1', '2', '3'], help='Scenario number')
    args = parser.parse_args()

    # config 로드
    cfg = TestConfig(args.config)
    with open(args.config, 'r') as f:
        cfg_json = json.load(f)

    scale_up_nodes = cfg_json.get('scale_up_nodes', [])
    depths = cfg_json.get('depths', [])
    iterations = cfg_json.get('iterations', 1000)
    params = cfg.scenario_params.get(args.scenario, {})

    # DB 연결 및 graph_path 설정
    conn = psycopg.connect(**cfg.db_params)
    cur = conn.cursor()
    cur.execute("SET graph_path = vc_graph;")

    # 전체 Drone ID 목록 가져오기
    cur.execute("MATCH (d:Drone) RETURN d.id;")
    drones_list = [row[0] for row in cur.fetchall()]

    rows = []
    if args.scenario == '1':
        print("=== Running Scenario C-1: Real-Time Turn-Taking ===")
        scenario1_realtime_turntaking(cur, conn, cfg, params, scale_up_nodes, depths, iterations, rows, drones_list)
    elif args.scenario == '2':
        print("=== Running Scenario C-2: Chain-Churn ===")
        scenario2_chain_churn(cur, conn, cfg, params, scale_up_nodes, depths, iterations, rows, drones_list)
    else:
        print("=== Running Scenario C-3: Partition & Reconciliation ===")
        scenario3_partition_reconciliation(cur, conn, cfg, params, scale_up_nodes, depths, iterations, rows, drones_list)

    # 결과 CSV 저장
    result_dir = Path(ROOT) / 'data' / 'result'
    result_dir.mkdir(parents=True, exist_ok=True)
    output_file = result_dir / f"C_{args.scenario}_results.csv"
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['scenario','scale_up','depth','p50_ms','p95_ms','p99_ms','tps'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Results written to {output_file}")

    cur.close()
    conn.close()
