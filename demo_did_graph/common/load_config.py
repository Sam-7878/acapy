# load_config.py
import json
from pathlib import Path


# config/test_small.json
class TestConfig:
    def __init__(self, config_path: str):
        self._load(config_path)

    def _load(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 기본 속성 파싱
        self.test_name = data.get('test_name')
        self.db_type = data.get('db_type')  # 'postgres' or 'agensgraph'
        self.test_case = data.get('test_case')  # 'A', 'B', 'C'
        self.random_seed = data.get('random_seed', 42)
        self.enable_random_binding = data.get('enable_random_binding', True)
        self.log_output_path = data.get('log_output_path', 'test_log.json')

        # 노드 수 파싱
        self.num_mission = data['node_count']['mission']
        self.num_execution = data['node_count']['execution']
        self.num_verification = data['node_count']['verification']

        # DB 연결 설정
        self.db_config = data.get('db_config', {})
        self.db_host = self.db_config.get('host', 'localhost')
        self.db_port = self.db_config.get('port', 5433)
        self.db_name = self.db_config.get('dbname', 'edge')
        self.db_user = self.db_config.get('user', 'sam')
        self.db_password = self.db_config.get('password', 'dooley')

    def __str__(self):
        return f"[TestConfig: {self.test_name}, DB: {self.db_type}, Case: {self.test_case}]"

# 사용 예시
if __name__ == "__main__":
    config = TestConfig("common/config/test_small.json")
    print(config)
    print("Mission nodes:", config.num_mission)
