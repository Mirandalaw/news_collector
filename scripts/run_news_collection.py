"""뉴스 수집 실행 스크립트.

프로젝트 루트에서 실행:
    python -m scripts.run_news_collection

환경변수:
    DB_HOST      (기본값: localhost)
    DB_PORT      (기본값: 5432)
    DB_NAME      (기본값: news_collector)
    DB_USER      (기본값: 현재 OS 유저)
    DB_PASSWORD  (기본값: 빈 문자열)
    LOG_LEVEL    (기본값: INFO)
"""

import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (패키지 설치 없이 직접 실행 시)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.collectors.rss_collector import RssSource
from app.db.connection import DatabaseConfig
from app.services.news_ingestion_service import NewsIngestionService


def _setup_logging() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# RSS 소스 정의
# ---------------------------------------------------------------------------
# 소스 목록은 추후 app/sources/rss_sources.py 또는 외부 설정 파일로 분리 가능
_SOURCES: list[RssSource] = [
    RssSource(
        url="https://feeds.yna.co.kr/economy.xml",
        source_name="연합뉴스_경제",
        category="경제",
    ),
    RssSource(
        url="https://rss.hankyung.com/feed/it.xml",
        source_name="한국경제_IT",
        category="IT",
    ),
    RssSource(
        url="https://rss.hankyung.com/feed/economy.xml",
        source_name="한국경제_경제",
        category="경제",
    ),
]


def main() -> int:
    """수집 파이프라인 실행. 반환값은 exit code.

    - 0: 정상 종료 (부분 실패 포함)
    - 1: 전체 실패 (DB 접속 불가 또는 전체 소스 실패)
    """
    _setup_logging()
    logger = logging.getLogger(__name__)

    db_config = DatabaseConfig.from_env()

    logger.info(
        "실행 시작 | DB host=%s dbname=%s user=%s | 소스 수=%d",
        db_config.host,
        db_config.dbname,
        db_config.user,
        len(_SOURCES),
    )

    service = NewsIngestionService(db_config=db_config, sources=_SOURCES)

    try:
        report = service.run()
    except Exception:
        logger.exception("파이프라인 실행 실패 - DB 접속을 확인하세요")
        return 1

    if report.all_failed:
        logger.error("전체 소스 실패 - 결과 없음")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
