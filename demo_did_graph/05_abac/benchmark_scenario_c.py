#!/usr/bin/env python3
# benchmark_scenario_c.py
# Scenario C Non-optimized Benchmark: DID 인증 + AgensGraph(GraphDB)

import time
import psycopg
import json
import random
import argparse
import csv
from pathlib import Path
import sys

# 프로젝트 루트를 PYTHONPATH에 추가 (common 모듈 로드용)
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from common.load_config import TestConfig
from common.did_utils import load_private_key
from common.bench_utils import benchmark_query, benchmark_query_parametric
from setup_scenario_c import setup_database


def get_bench_query(hq_id: str, max_depth: int) -> str:
    return f"""
    MATCH (hq:HQ {{id:'{hq_id}'}})
      -[:DELEGATES*1..{max_depth}]->(d:Drone)
      <-[:ASSERTS]-(v:VC)
    RETURN count(v) AS vc_count;
    """


def scenario1_realtime_turntaking(cfg, params, iterations, rows, private_key):
    # 단일 커넥션으로 전체 스케일 단계 수행 (비최적화)
    scale_up_nodes = cfg.scale_up_nodes
    depths = cfg.depths
    ratio = params['1']['turn_taking']['update_ratio']

    for num_nodes in scale_up_nodes:
        # 2) 그래프 DROP/CREATE (별도 커넥션)
        print(f"\n-- Init DB : update_count based on {num_nodes} nodes (Turn-Taking) --")
        setup_database(cfg, private_key, 1)

        # 3) 벤치마크용 커넥션 재생성 및 graph_path 재설정
        conn = psycopg.connect(**cfg.db_params)
        cur = conn.cursor()
        cur.execute("SET graph_path = vc_graph;")

        # 최신 Drone ID 목록 조회
        cur.execute("MATCH (d:Drone) RETURN d.id;")
        drones_list = [r[0] for r in cur.fetchall()]

        print(f"\n-- Scale-up: update_count based on {num_nodes} nodes (Turn-Taking) --")
        
        for depth in depths:
            # 업데이트 대상 수 계산
            update_count = int(num_nodes * ratio)
            selected = random.sample(drones_list, update_count)

            for i in selected:
                did = f"drone:{i}"
                cur.execute(f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;")
            for i in selected:
                did = f"drone:{i}"
                cur.execute(f"MATCH (hq:HQ {{id:'{cfg.headquarters_id}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);")
            conn.commit()

            query = get_bench_query(cfg.headquarters_id, depth)
            # 벤치마크
            p50, p95, p99, tps = benchmark_query(cur, query, iterations)

            print(f"Depth {depth} → P50: {p50*1000:.2f} ms, P95: {p95*1000:.2f} ms, P99: {p99*1000:.2f} ms, TPS: {tps:.2f}")
            rows.append({
                'scenario': f'B-1',
                'scale_up': num_nodes,
                'depth': depth,
                'p50_ms': p50*1000,
                'p95_ms': p95*1000,
                'p99_ms': p99*1000,
                'tps': tps
            })
        cur.close()
        conn.close()


def scenario2_chain_churn(cfg, params, iterations, rows, private_key):
    conn = psycopg.connect(**cfg.db_params)
    cur = conn.cursor()

    hq = cfg.headquarters_id
    scale_nodes = params['chain_churn']['scale_up_nodes']
    depths = params['chain_churn']['depths']
    ratio = params['chain_churn']['churn_ratio']

    for nodes in scale_nodes:
        for depth in depths:
            churn = int(nodes * ratio)
            ids = random.sample(range(nodes), churn)
            for i in ids:
                did = f"drone:{i}"
                cur.execute(f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;")
            for i in ids:
                did = f"drone:{i}"
                cur.execute(f"MATCH (hq:HQ {{id:'{hq}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);")
            conn.commit()

            query = get_bench_query(hq, depth)
            p50, p95, p99, tps = benchmark_query(cur, query, iterations)
            rows.append(["scenario2", nodes, depth, p50, p95, p99, tps])

    cur.close()
    conn.close()


def scenario3_partition_reconciliation(cfg, params, iterations, rows, private_key):
    conn = psycopg.connect(**cfg.db_params)
    cur = conn.cursor()

    hq = cfg.headquarters_id
    parts = params['partition_reconciliation']['partitions']
    depths = params['partition_reconciliation']['depths']
    syncs = params['partition_reconciliation']['post_reconcile_sync_requests']

    for part in parts:
        for depth in depths:
            for i in part:
                did = f"drone:{i}"
                cur.execute(f"MATCH ()-[r:DELEGATES]->(d:Drone {{id:'{did}'}}) DELETE r;")
                cur.execute(f"MATCH (hq:HQ {{id:'{hq}'}}),(d:Drone {{id:'{did}'}}) CREATE (hq)-[:DELEGATES]->(d);")
            conn.commit()

            for _ in range(syncs):
                query = get_bench_query(hq, depth)
                p50, p95, p99, tps = benchmark_query(cur, query, iterations)
            rows.append(["scenario3", part, depth, p50, p95, p99, tps])

    cur.close()
    conn.close()


def scenario4_web_of_trust(cfg, params, iterations, rows):
    conn = psycopg.connect(**cfg.db_params)
    cur = conn.cursor()

    # use the correct graph
    cur.execute("SET graph_path = trust_graph;")

    # 설정 파일의 시나리오 4 파라미터 사용
    wp = params['4']['web_of_trust']
    anchor = wp['anchor_did']
    # clients = wp['clients']
    lengths = wp['max_path_lengths']

    # 클라이언트 후보 추출
    cur.execute("MATCH (e:Entity) WHERE e.did <> '{0}' RETURN e.did;".format(anchor))
    candidates = [r[0] for r in cur.fetchall()]

    for length in lengths:
        client = random.choice(candidates)
        # Web-of-Trust 경로 탐색 쿼리
        query = f"MATCH path=(c:Entity {{did:'{client}'}})-[:CROSSED_SIGNED*1..{length}]->(a:Entity {{did:'{anchor}'}}) RETURN count(path);"

        p50, p95, p99, tps = benchmark_query(cur, query, iterations)

        print(f"[WebTrust len={length}] P50={p50*1000:.2f}ms, p95={p95*1000:.2f}ms, p99={p99*1000:.2f}ms, TPS={tps:.2f}")
        rows.append({
            'scenario':'C-4', 
            'scale_up':'', 
            'length':length, 
            'p50_ms':p50*1000, 
            'p95_ms':p95*1000, 
            'p99_ms':p99*1000, 
            'tps':tps
        })

    cur.close()
    conn.close()



def scenario5_abac(cfg, params, iterations, rows):
    conn = psycopg.connect(**cfg.db_params)
    cur = conn.cursor()

    users = params['abac']['users']
    depths = params['abac']['depths']
    resource = params['abac']['resource_id']

    for user in users:
        for depth in depths:
            query = f"WITH RECURSIVE chain(u, g, lvl) AS (SELECT u, g, 1 FROM AppUser u WHERE did='{user}' UNION ALL SELECT u2, g2, lvl+1 FROM chain c JOIN AppGroup g2 ON c.g = g2.id WHERE lvl < {depth}) SELECT count(*) FROM chain;"
 
            p50, p95, p99, tps = benchmark_query(cur, query, iterations)

            rows.append(["scenario5", user, depth, p50, p95, p99, tps])

    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Non-optimized Scenario C Benchmark")
    parser.add_argument('-c', '--config', required=True)
    parser.add_argument('-s', '--scenario', required=True, choices=['1','2','3','4','5'])
    args = parser.parse_args()

    cfg = TestConfig(args.config)
    private_key = load_private_key(cfg.private_key_path)
    params = cfg.scenario_params
    iterations = cfg.iterations

    rows = []
    setup_database(cfg, private_key, int(args.scenario))

    if args.scenario == '1':
        scenario1_realtime_turntaking(cfg, params, iterations, rows, private_key)
    elif args.scenario == '2':
        scenario2_chain_churn(cfg, params, iterations, rows, private_key)
    elif args.scenario == '3':
        scenario3_partition_reconciliation(cfg, params, iterations, rows, private_key)
    elif args.scenario == '4':
        scenario4_web_of_trust(cfg, params, iterations, rows)
    elif args.scenario == '5':
        scenario5_abac(cfg, params, iterations, rows)


    # 결과 저장
    result_dir = Path(ROOT) / cfg.data_result_path
    result_dir.mkdir(parents=True, exist_ok=True)
    output_file = result_dir / f"C_{args.scenario}_results.csv"
    with open(output_file, 'w', newline='') as f:
        cols = []
        if args.scenario in ['1', '2', '3']:
            cols = ['scenario', 'scale_up', 'depth', 'p50_ms', 'p95_ms', 'p99_ms', 'tps']
        elif args.scenario == '4':
            cols = ['scenario', 'scale_up', 'length', 'p50_ms', 'p95_ms', 'p99_ms', 'tps']
        elif args.scenario == '5':
            cols = ['scenario', 'scale_up', 'depth', 'p50_ms', 'p95_ms', 'p99_ms', 'tps']

        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Results written to {output_file}")


if __name__ == '__main__':
    main()
