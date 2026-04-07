"""뉴스 수집 Job.

run_collect(config) → JobResult

RSS 소스 목록에서 뉴스를 수집해 DB에 저장하는 단일 함수.
스크립트 / 스케줄러 어디서든 직접 호출 가능.
"""

import logging
from datetime import datetime, timezone

from app.collectors.rss_collector import RssSource
from app.db.connection import DatabaseConfig
from app.jobs.base import JobResult
from app.services.news_ingestion_service import NewsIngestionService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RSS 소스 목록 (app/sources/rss_sources.py 로 분리 시 이동 예정)
# ---------------------------------------------------------------------------

DEFAULT_SOURCES: list[RssSource] = [
    # ── 매일경제 ──────────────────────────────────────────────────
    RssSource(url="https://www.mk.co.kr/rss/30000001/", source_name="매일경제", category="경제"),
    RssSource(
        url="https://www.mk.co.kr/rss/30100041/", source_name="매일경제_주식", category="증권"
    ),
    RssSource(
        url="https://www.mk.co.kr/rss/30300018/", source_name="매일경제_국제", category="국제"
    ),
    RssSource(
        url="https://www.mk.co.kr/rss/30200030/", source_name="매일경제_IT", category="IT"
    ),
    # ── 한국경제 ──────────────────────────────────────────────────
    RssSource(
        url="https://www.hankyung.com/feed/all-news", source_name="한국경제", category="경제"
    ),
    RssSource(
        url="https://www.hankyung.com/feed/finance", source_name="한국경제_증권", category="증권"
    ),
    RssSource(url="https://www.hankyung.com/feed/it", source_name="한국경제_IT", category="IT"),
    RssSource(
        url="https://www.hankyung.com/feed/international",
        source_name="한국경제_국제",
        category="국제",
    ),
    # ── 전자신문 ──────────────────────────────────────────────────
    RssSource(
        url="https://rss.etnews.com/Section901.xml", source_name="전자신문", category="IT"
    ),
    RssSource(
        url="https://rss.etnews.com/Section902.xml", source_name="전자신문_ICT", category="IT"
    ),
]


# ---------------------------------------------------------------------------
# Job 진입점
# ---------------------------------------------------------------------------


def run_collect(
    db_config: DatabaseConfig,
    sources: list[RssSource] | None = None,
) -> JobResult:
    """뉴스 수집 파이프라인을 실행하고 JobResult를 반환한다.

    Args:
        db_config: DB 접속 설정
        sources: RSS 소스 목록. None이면 DEFAULT_SOURCES 사용.

    Returns:
        JobResult — exit_code 속성으로 프로세스 종료 코드 결정
    """
    sources = sources or DEFAULT_SOURCES
    started = datetime.now(timezone.utc)

    logger.info(
        "뉴스 수집 시작 | DB=%s/%s | 소스=%d개",
        db_config.host,
        db_config.dbname,
        len(sources),
    )

    try:
        service = NewsIngestionService(db_config=db_config, sources=sources)
        report = service.run()
    except Exception as e:
        logger.exception("수집 파이프라인 오류")
        return JobResult(
            job_name="collect",
            success=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail="파이프라인 실행 실패 — DB 접속을 확인하세요",
            error=e,
        )

    finished = datetime.now(timezone.utc)
    success = not report.all_failed

    detail = (
        f"수집={report.total_collected} / 저장={report.total_inserted} / "
        f"중복={report.total_skipped} / 태깅={report.total_tagged} / "
        f"실패소스={len(report.failed_sources)}/{len(sources)}"
    )

    logger.info("수집 완료 | %s", detail)
    if report.all_failed:
        logger.error("전체 소스 실패")

    return JobResult(
        job_name="collect",
        success=success,
        started_at=started,
        finished_at=finished,
        detail=detail,
    )
