"""검수 서비스. 조회 → 이슈 감지 → ReviewResult 반환."""

import logging
from datetime import datetime

import psycopg2

from app.db.connection import DatabaseConfig, managed_connection
from app.review.checks import detect_issues
from app.review.models import ReviewResult
from app.review.query import fetch_all_articles

logger = logging.getLogger(__name__)


class ReviewService:
    """브리핑 품질 검수 파이프라인.

    Args:
        db_config: PostgreSQL 접속 설정
        article_limit: 단일 조회 최대 기사 수 (기본 500)
    """

    def __init__(self, db_config: DatabaseConfig, article_limit: int = 500) -> None:
        self._db_config = db_config
        self._article_limit = article_limit

    def run(self, since: datetime, until: datetime) -> ReviewResult:
        """지정한 시간 범위의 기사를 조회하고 이슈를 감지해 반환한다.

        Args:
            since: 수집 시각 기준 시작 (UTC, inclusive)
            until: 수집 시각 기준 종료 (UTC, exclusive)

        Returns:
            ReviewResult

        Raises:
            psycopg2.OperationalError: DB 접속 실패 시
        """
        logger.info(
            "검수 조회 시작 | since=%s ~ until=%s",
            since.strftime("%Y-%m-%d %H:%M UTC"),
            until.strftime("%Y-%m-%d %H:%M UTC"),
        )

        try:
            with managed_connection(self._db_config) as conn:
                articles = fetch_all_articles(conn, since, until, limit=self._article_limit)
        except psycopg2.Error:
            logger.exception("검수 조회 실패")
            raise

        logger.info("기사 조회 완료 | %d건", len(articles))

        issues = detect_issues(articles)
        logger.info(
            "이슈 감지 완료 | 총 %d건 | no_summary=%d / duplicate=%d / untagged=%d / misclassify=%d",
            len(issues),
            sum(1 for i in issues if i.kind.value == "no_summary"),
            sum(1 for i in issues if i.kind.value == "duplicate_hash"),
            sum(1 for i in issues if i.kind.value == "untagged_watchlist"),
            sum(1 for i in issues if i.kind.value == "misclassification"),
        )

        return ReviewResult(since=since, until=until, articles=articles, issues=issues)
