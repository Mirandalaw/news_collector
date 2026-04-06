"""수집 → 브리핑 순차 실행 진입점 (cron 단일 엔트리).

collect job 실패 시에도 briefing job을 실행할지 여부를 --skip-on-collect-fail 로 제어.
기본값은 수집 실패해도 브리핑 시도 (이전 수집분으로 브리핑 가능하므로).

cron 예시 (단일 작업):
  0 6 * * *  /path/to/.venv/bin/python /path/to/scripts/run_all.py --telegram --no-console

환경 변수:
  DB_*                    — DB 접속
  TELEGRAM_BOT_TOKEN      — 텔레그램 봇 토큰
  TELEGRAM_CHAT_ID        — 텔레그램 채팅 ID
  LOG_LEVEL               — 기본 INFO
  LOG_DIR                 — 로그 파일 저장 디렉토리 (기본: logs/)
  BRIEFING_HOURS_BACK     — 조회 시간 범위 (기본: 12)
  BRIEFING_OUTPUT_DIR     — 파일 저장 경로 (기본: output/)
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig
from app.jobs.base import JobResult, setup_job_logging
from app.jobs.briefing_job import BriefingJobConfig, build_publishers, run_briefing
from app.jobs.collect_job import run_collect
from app.summarizers.mock_summarizer import MockSummarizer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="수집 → 브리핑 순차 실행")

    parser.add_argument("--telegram",            action="store_true")
    parser.add_argument("--save",                action="store_true")
    parser.add_argument("--save-fmt",            default="text", choices=["text", "json"])
    parser.add_argument("--save-dir",            default=os.environ.get("BRIEFING_OUTPUT_DIR", "output"))
    parser.add_argument("--no-console",          action="store_true")
    parser.add_argument("--mock",                action="store_true")
    parser.add_argument("--hours",               type=int,
                        default=int(os.environ.get("BRIEFING_HOURS_BACK", "12")))
    parser.add_argument("--skip-on-collect-fail", action="store_true",
                        help="수집 실패 시 브리핑 건너뜀 (기본: 브리핑 시도)")

    return parser.parse_args()


def main() -> int:
    args    = _parse_args()
    log_dir = os.environ.get("LOG_DIR", "logs")
    logger  = setup_job_logging("all", os.environ.get("LOG_LEVEL", "INFO"), log_dir)
    db_cfg  = DatabaseConfig.from_env()

    # ── 1단계: 수집 ────────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info("STEP 1 / 2  뉴스 수집")
    logger.info("=" * 50)
    collect_result = run_collect(db_config=db_cfg)
    collect_result.log_summary(logger)

    if not collect_result.success and args.skip_on_collect_fail:
        logger.error("수집 실패로 브리핑을 건너뜁니다.")
        return collect_result.exit_code

    # ── 2단계: 브리핑 ──────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info("STEP 2 / 2  브리핑 생성 + 전송")
    logger.info("=" * 50)

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

    briefing_result = run_briefing(db_config=db_cfg, job_config=job_config)
    briefing_result.log_summary(logger)

    # ── 최종 요약 ──────────────────────────────────────────────────
    logger.info("=" * 50)
    all_ok = collect_result.success and briefing_result.success
    total_elapsed = (
        (collect_result.elapsed_seconds or 0) + (briefing_result.elapsed_seconds or 0)
    )
    logger.info(
        "전체 완료 | collect=%s / briefing=%s | 총 %.1f초",
        "OK" if collect_result.success else "FAIL",
        "OK" if briefing_result.success else "FAIL",
        total_elapsed,
    )

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
