#!/usr/bin/env python3
"""
Configuration module that loads all settings from .env file.
No hardcoded credentials - everything comes from environment.
"""
import os
from dotenv import load_dotenv

# Load .env file from the same directory as this script
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)


class Config:
    """
    Configuration class that reads all values from .env file.
    Provides type conversion and validation.
    """

    # CSS Cluster Configuration
    css_host: str = os.getenv('CSS_HOST', 'localhost')
    css_port: int = int(os.getenv('CSS_PORT', '9200'))
    css_username: str = os.getenv('CSS_USERNAME', 'admin')
    css_password: str = os.getenv('CSS_PASSWORD', '')
    css_cluster_id: str = os.getenv('CSS_CLUSTER_ID', 'css-test')

    # Index Configuration
    index_name: str = os.getenv('INDEX_NAME', 'benchmark_vectors')
    vector_dimension: int = int(os.getenv('VECTOR_DIMENSION', '128'))

    # Huawei Cloud API Credentials
    hw_access_key: str = os.getenv('HW_ACCESS_KEY', '')
    hw_secret_key: str = os.getenv('HW_SECRET_KEY', '')
    hw_project_id: str = os.getenv('HW_PROJECT_ID', '')
    hw_region: str = os.getenv('HW_REGION', 'la-north-2')

    # Benchmark Configuration
    ingestion_total_vectors: int = int(os.getenv('INGESTION_TOTAL_VECTORS', '10000'))
    ingestion_batch_size: int = int(os.getenv('INGESTION_BATCH_SIZE', '100'))
    eval_n_queries: int = int(os.getenv('EVAL_N_QUERIES', '100'))
    eval_corpus_size: int = int(os.getenv('EVAL_CORPUS_SIZE', '1000'))
    rds_simulation_rows: int = int(os.getenv('RDS_SIMULATION_ROWS', '50000'))

    # Autoscaling Thresholds
    scale_out_cpu: int = int(os.getenv('SCALE_OUT_CPU_THRESHOLD', '75'))
    scale_out_heap: int = int(os.getenv('SCALE_OUT_HEAP_THRESHOLD', '80'))
    scale_out_disk: int = int(os.getenv('SCALE_OUT_DISK_THRESHOLD', '75'))

    scale_in_cpu: int = int(os.getenv('SCALE_IN_CPU_THRESHOLD', '30'))
    scale_in_heap: int = int(os.getenv('SCALE_IN_HEAP_THRESHOLD', '40'))
    scale_in_disk: int = int(os.getenv('SCALE_IN_DISK_THRESHOLD', '40'))

    min_data_nodes: int = int(os.getenv('MIN_DATA_NODES', '3'))
    max_data_nodes: int = int(os.getenv('MAX_DATA_NODES', '10'))

    scale_out_cooldown: int = int(os.getenv('SCALE_OUT_COOLDOWN', '300'))
    scale_in_cooldown: int = int(os.getenv('SCALE_IN_COOLDOWN', '600'))
    monitor_interval: int = int(os.getenv('MONITOR_INTERVAL', '30'))

    # Phase 5 Controller Configuration
    phase5_check_interval: int = int(os.getenv('PHASE5_CHECK_INTERVAL', '5'))
    phase5_scale_out_target_time: int = int(os.getenv('PHASE5_SCALE_OUT_TARGET_TIME', '120'))
    phase5_scale_in_target_time: int = int(os.getenv('PHASE5_SCALE_IN_TARGET_TIME', '180'))
    phase5_max_scale_out_retries: int = int(os.getenv('PHASE5_MAX_SCALE_OUT_RETRIES', '5'))
    phase5_max_total_iterations: int = int(os.getenv('PHASE5_MAX_TOTAL_ITERATIONS', '500'))
    phase5_cooldown_time: int = int(os.getenv('PHASE5_COOLDOWN_TIME', '30'))
    phase5_locust_processes: int = int(os.getenv('PHASE5_LOCUST_PROCESSES', '4'))  # Número de procesos Locust

    @property
    def css_url(self) -> str:
        """Return full CSS URL with https://"""
        return f"https://{self.css_host}"

    @property
    def css_full_url(self) -> str:
        """Return full CSS URL with port"""
        return f"https://{self.css_host}:{self.css_port}"

    def get_opensearch_config(self) -> dict:
        """Return configuration dict for OpenSearch client"""
        return {
            'hosts': [{'host': self.css_host, 'port': self.css_port}],
            'http_auth': (self.css_username, self.css_password),
            'use_ssl': True,
            'verify_certs': False,
            'ssl_show_warn': False,
        }

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return (is_valid, errors)"""
        errors = []

        if not self.css_host:
            errors.append("CSS_HOST not set")
        if not self.css_password:
            errors.append("CSS_PASSWORD not set")
        if not self.hw_access_key:
            errors.append("HW_ACCESS_KEY not set")
        if not self.hw_secret_key:
            errors.append("HW_SECRET_KEY not set")
        if not self.hw_project_id:
            errors.append("HW_PROJECT_ID not set")

        return len(errors) == 0, errors

    def __repr__(self) -> str:
        """Safe string representation (hides passwords)"""
        return (
            f"Config(css_host='{self.css_host}', "
            f"css_port={self.css_port}, "
            f"css_username='{self.css_username}', "
            f"css_password='***', "
            f"index_name='{self.index_name}', "
            f"vector_dimension={self.vector_dimension})"
        )


# Global config instance
config = Config()


if __name__ == "__main__":
    # Test configuration loading
    print("=" * 60)
    print("CONFIGURATION TEST")
    print("=" * 60)

    is_valid, errors = config.validate()

    if is_valid:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   • {error}")

    print(f"\nConfiguration loaded from: {_env_path}")
    print(f"\n{config}")

    print(f"\nCSS URL: {config.css_full_url}")
    print(f"OpenSearch config: {config.get_opensearch_config()}")
