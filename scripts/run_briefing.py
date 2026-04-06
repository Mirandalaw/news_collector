"""브리핑 생성 + 전송 실행 진입점.

사용법:
  python scripts/run_briefing.py                    # 콘솔 출력
  python scripts/run_briefing.py --telegram         # 텔레그램 전송
  python scripts/run_briefing.py --save             # 파일 저장
  python scripts/run_briefing.py --save --telegram  # 파일 + 텔레그램
  python scripts/run_briefing.py --no-console --telegram  # 텔레그램 전용

cron / systemd 예시:
  10 6 * * *  /path/to/.venv/bin/python /path/to/scripts/run_briefing.py --telegram --no-console

환경변수:
  DB_*                       — DB 접속
  TELEGRAM_BOT_TOKEN         — 텔레그램 봇 토큰
  TELEGRAM_CHAT_ID           — 텔레그램 채팅 ID
  LOG_LEVEL                  — 기본 INFO
  LOG_DIR                    — 로그 파일 저장 디렉토리 (기본: logs/)
  BRIEFING_HOURS_BACK        — 조회 시간 범위 (기본: 12)
  BRIEFING_OUTPUT_DIR        — 파일 저장 경로 (기본: output/)
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig
from app.db.repositories.metrics_repository import try_record_job_run
from app.jobs.base import setup_job_logging
from app.jobs.briefing_job import BriefingJobConfig, build_publishers, run_briefing
from app.summarizers.mock_summarizer import MockSummarizer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="아침 브리핑 생성 및 전송")

    parser.add_argument("--telegram", action="store_true", help="텔레그램으로 전송")
    parser.add_argument("--save", action="store_true", help="파일로 저장")
    parser.add_argument("--save-fmt", default="text", choices=["text", "json"])
    parser.add_argument("--save-dir", default=os.environ.get("BRIEFING_OUTPUT_DIR", "output"))
    parser.add_argument("--no-console", action="store_true", help="콘솔 출력 비활성화")
    parser.add_argument("--mock", action="store_true", help="MockSummarizer 사용")
    parser.add_argument(
        "--hours", type=int, default=int(os.environ.get("BRIEFING_HOURS_BACK", "12"))
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    log_dir = os.environ.get("LOG_DIR", "logs")
    logger = setup_job_logging("briefing", os.environ.get("LOG_LEVEL", "INFO"), log_dir)
    db_config = DatabaseConfig.from_env()

    publishers = build_publishers(
        console=not args.no_console,
        file_dir=args.save_dir if args.save else None,
        file_fmt=args.save_fmt,
        telegram=args.telegram,
    )

    job_config = BriefingJobConfig(
        hours_back=args.hours,
        summarizer=MockSummarizer() if args.mock else None,
        publishers=publishers,
    )

    result = run_briefing(db_config=db_config, job_config=job_config)
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
