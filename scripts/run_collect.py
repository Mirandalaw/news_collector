"""뉴스 ��집 실행 진입점.

cron / systemd 예시:
  0 6 * * *  /path/to/.venv/bin/python /path/to/scripts/run_collect.py

환경변수:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  — DB 접속
  LOG_LEVEL   — 로그 레벨 (기본: INFO)
  LOG_DIR     — 로그 파일 저장 디렉토리 (기본: logs/, 비우면 파일 없음)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig
from app.db.repositories.metrics_repository import try_record_job_run
from app.jobs.base import setup_job_logging
from app.jobs.collect_job import run_collect


def main() -> int:
    log_dir = os.environ.get("LOG_DIR", "logs")
    logger = setup_job_logging("collect", os.environ.get("LOG_LEVEL", "INFO"), log_dir)
    db_config = DatabaseConfig.from_env()

    result = run_collect(db_config=db_config)
    result.log_summary(logger)

    try_record_job_run(
        db_config=db_config,
        job_name=result.job_name,
        started_at=result.started_at,
        finished_at=result.finished_at,
        success=result.success,
        elapsed_secs=result.elapsed_seconds,
        detail=result.detail,
        error_msg=str(result.error) if result.error else "",
    )

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
