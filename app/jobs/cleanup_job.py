"""데이터 보존 정책 기반 cleanup Job.

cleanup_articles(db_config, dry_run) → dict
cleanup_metrics(db_config, dry_run) → dict
main() → int

보존 정책:
  news_articles  collected_at 기준 90일 초과 → DELETE
  job_metrics    started_at 기준 30일 초과 → DELETE
  article_symbols ON DELETE CASCADE (별도 처리 불필요)

사용법:
  python app/jobs/cleanup_job.py --dry-run --target all
  python app/jobs/cleanup_job.py --target articles
  python app/jobs/cleanup_job.py --target metrics
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db.connection import DatabaseConfig, managed_connection
from app.db.repositories.metrics_repository import try_record_job_run
from app.jobs.base import JobResult, setup_job_logging

logger = logging.getLogger(__name__)

ARTICLES_RETENTION_DAYS = 90
METRICS_RETENTION_DAYS = 30
BATCH_SIZE = 1000

# dry-run: 삭제 대상 건수 조회
_COUNT_ARTICLES = """
SELECT COUNT(*)
FROM news_articles
WHERE collected_at < NOW() - (%(days)s || ' days')::INTERVAL;
"""

_COUNT_METRICS = """
SELECT COUNT(*)
FROM job_metrics
WHERE started_at < NOW() - (%(days)s || ' days')::INTERVAL;
"""

# live: batch delete
_DELETE_ARTICLES_BATCH = """
DELETE FROM news_articles
WHERE id IN (
    SELECT id FROM news_articles
    WHERE collected_at < NOW() - (%(days)s || ' days')::INTERVAL
    LIMIT %(batch_size)s
);
"""

_DELETE_METRICS_BATCH = """
DELETE FROM job_metrics
WHERE id IN (
    SELECT id FROM job_metrics
    WHERE started_at < NOW() - (%(days)s || ' days')::INTERVAL
    LIMIT %(batch_size)s
);
"""


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _batch_delete(db_config: DatabaseConfig, sql: str, params: dict) -> int:
    """batch 단위로 DELETE를 반복 실행하고 총 삭제 건수를 반환한다.

    - 단일 커넥션을 유지하며 batch마다 commit
    - rowcount == 0이면 종료 (대상 소진)
    """
    total = 0
    with managed_connection(db_config) as conn:
        while True:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                deleted = cur.rowcount
            conn.commit()
            if deleted == 0:
                break
            total += deleted
            logger.debug("batch 삭제 | %d건 (누적 %d건)", deleted, total)
    return total


# ---------------------------------------------------------------------------
# cleanup 함수
# ---------------------------------------------------------------------------


def cleanup_articles(db_config: DatabaseConfig, dry_run: bool) -> dict:
    """news_articles에서 보존 기간 초과 데이터를 조회(dry-run) 또는 삭제한다.

    Args:
        db_config: DB 접속 설정
        dry_run: True면 SELECT COUNT만 실행, False면 batch DELETE 수행

    Returns:
        {"count": int} — 삭제 대상(dry-run) 또는 실제 삭제(live) 건수
    """
    if dry_run:
        with managed_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(_COUNT_ARTICLES, {"days": ARTICLES_RETENTION_DAYS})
                count: int = cur.fetchone()[0]
        logger.info(
            "[DRY-RUN] cleanup_articles | 삭제 대상=%d건 (retention=%d일)",
            count,
            ARTICLES_RETENTION_DAYS,
        )
        return {"count": count}

    count = _batch_delete(
        db_config,
        _DELETE_ARTICLES_BATCH,
        {"days": ARTICLES_RETENTION_DAYS, "batch_size": BATCH_SIZE},
    )
    logger.info(
        "[DELETE] cleanup_articles | 삭제 완료=%d건 (retention=%d일)",
        count,
        ARTICLES_RETENTION_DAYS,
    )
    return {"count": count}


def cleanup_metrics(db_config: DatabaseConfig, dry_run: bool) -> dict:
    """job_metrics에서 보존 기간 초과 데이터를 조회(dry-run) 또는 삭제한다.

    Args:
        db_config: DB 접속 설정
        dry_run: True면 SELECT COUNT만 실행, False면 batch DELETE 수행

    Returns:
        {"count": int} — 삭제 대상(dry-run) 또는 실제 삭제(live) 건수
    """
    if dry_run:
        with managed_connection(db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(_COUNT_METRICS, {"days": METRICS_RETENTION_DAYS})
                count: int = cur.fetchone()[0]
        logger.info(
            "[DRY-RUN] cleanup_metrics | 삭제 대상=%d건 (retention=%d일)",
            count,
            METRICS_RETENTION_DAYS,
        )
        return {"count": count}

    count = _batch_delete(
        db_config,
        _DELETE_METRICS_BATCH,
        {"days": METRICS_RETENTION_DAYS, "batch_size": BATCH_SIZE},
    )
    logger.info(
        "[DELETE] cleanup_metrics | 삭제 완료=%d건 (retention=%d일)",
        count,
        METRICS_RETENTION_DAYS,
    )
    return {"count": count}


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="데이터 보존 정책 기반 cleanup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 삭제 없이 대상 건수만 확인",
    )
    parser.add_argument(
        "--target",
        choices=["articles", "metrics", "all"],
        default="all",
        help="cleanup 대상 (기본: all)",
    )
    return parser.parse_args()


def _build_detail(target: str, articles: dict, metrics: dict, dry_run: bool) -> str:
    label = "대상" if dry_run else "삭제"
    parts = []
    if target in ("articles", "all"):
        parts.append(f"articles {label}={articles.get('count', 0)}")
    if target in ("metrics", "all"):
        parts.append(f"metrics {label}={metrics.get('count', 0)}")
    return " | ".join(parts)


def main() -> int:
    args = _parse_args()
    log_dir = os.environ.get("LOG_DIR", "logs")
    job_logger = setup_job_logging("cleanup", os.environ.get("LOG_LEVEL", "INFO"), log_dir)
    db_config = DatabaseConfig.from_env()
    started = datetime.now(timezone.utc)

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    job_logger.info("cleanup 시작 | target=%s | mode=%s", args.target, mode)

    try:
        articles_result: dict = {}
        metrics_result: dict = {}

        if args.target in ("articles", "all"):
            articles_result = cleanup_articles(db_config, args.dry_run)
        if args.target in ("metrics", "all"):
            metrics_result = cleanup_metrics(db_config, args.dry_run)

        detail = _build_detail(args.target, articles_result, metrics_result, args.dry_run)
        result = JobResult(
            job_name="cleanup",
            success=True,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail=detail,
        )
    except Exception as e:
        job_logger.exception("cleanup 오류")
        result = JobResult(
            job_name="cleanup",
            success=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail="실행 실패",
            error=e,
        )

    result.log_summary(job_logger)

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
