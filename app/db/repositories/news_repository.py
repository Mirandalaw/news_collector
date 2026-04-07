"""news_articles 테이블 대상 데이터 접근 모듈.

외부에서 커넥션을 주입받아 DML을 처리한다.
각 함수는 트랜잭션(commit/rollback)을 내부에서 완결한다.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import psycopg2.errors
import psycopg2.extensions

logger = logging.getLogger(__name__)

_INSERT_NEWS_ARTICLE = """
INSERT INTO news_articles (
    source_name,
    category,
    title,
    url,
    published_at,
    summary,
    collected_at,
    title_hash,
    article_type
) VALUES (
    %(source_name)s,
    %(category)s,
    %(title)s,
    %(url)s,
    %(published_at)s,
    %(summary)s,
    %(collected_at)s,
    %(title_hash)s,
    %(article_type)s
)
ON CONFLICT (url) DO UPDATE
    SET article_type = EXCLUDED.article_type
    WHERE news_articles.article_type = 'general'
RETURNING (xmax = 0) AS is_new;
"""


@dataclass(frozen=True)
class NewsArticle:
    source_name: str
    category: str
    title: str
    url: str
    collected_at: datetime
    published_at: datetime | None = None
    summary: str = ""
    title_hash: str = ""  # SHA-256(normalize(title)). 빈 문자열 = 미계산
    article_type: str = "general"  # 의미 분류: market | company | event | general


def insert_article(
    conn: psycopg2.extensions.connection,
    article: NewsArticle,
) -> bool:
    """뉴스 기사 1건을 삽입한다.

    URL이 이미 존재하고 article_type이 'general'이면 재분류(UPDATE)한다.
    URL이 이미 존재하고 article_type이 이미 분류된 경우 아무것도 하지 않는다.
    삽입 성공 시 commit, 실패 시 rollback한다.

    Args:
        conn: psycopg2 커넥션 (autocommit=False 상태여야 함)
        article: 저장할 뉴스 기사 데이터

    Returns:
        True  - 신규 삽입 성공
        False - URL 중복(재분류 포함)으로 skip

    Raises:
        psycopg2.Error: 예상치 못한 DB 오류 발생 시 rollback 후 재발생
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                _INSERT_NEWS_ARTICLE,
                {
                    "source_name": article.source_name,
                    "category": article.category,
                    "title": article.title,
                    "url": article.url,
                    "published_at": article.published_at,
                    "summary": article.summary,
                    "collected_at": article.collected_at,
                    "title_hash": article.title_hash or None,
                    "article_type": article.article_type,
                },
            )
            row = cur.fetchone()
            inserted = bool(row and row[0])  # is_new=True → 신규 INSERT
        conn.commit()

        if inserted:
            logger.info("저장 성공 | source=%s | url=%s", article.source_name, article.url)
        else:
            logger.debug("중복 스킵 | source=%s | url=%s", article.source_name, article.url)

        return inserted

    except psycopg2.Error:
        conn.rollback()
        logger.exception(
            "저장 실패 - rollback | source=%s | url=%s", article.source_name, article.url
        )
        raise


def insert_articles(
    conn: psycopg2.extensions.connection,
    articles: list[NewsArticle],
) -> tuple[int, int]:
    """뉴스 기사 목록을 단일 트랜잭션으로 일괄 삽입한다.

    한 건이라도 예상치 못한 오류가 발생하면 전체 rollback한다.
    URL 중복은 오류로 취급하지 않고 건너뛴다.

    Args:
        conn: psycopg2 커넥션
        articles: 저장할 뉴스 기사 목록

    Returns:
        (inserted_count, skipped_count) 튜플

    Raises:
        psycopg2.Error: 예상치 못한 DB 오류 발생 시 rollback 후 재발생
    """
    inserted_count = 0
    skipped_count = 0

    try:
        with conn.cursor() as cur:
            for article in articles:
                cur.execute(
                    _INSERT_NEWS_ARTICLE,
                    {
                        "source_name": article.source_name,
                        "category": article.category,
                        "title": article.title,
                        "url": article.url,
                        "published_at": article.published_at,
                        "summary": article.summary,
                        "collected_at": article.collected_at,
                        "title_hash": article.title_hash or None,
                        "article_type": article.article_type,
                    },
                )
                row = cur.fetchone()
                if row and row[0]:  # is_new=True → 신규 INSERT
                    inserted_count += 1
                    logger.debug("저장 대상 | url=%s", article.url)
                else:
                    skipped_count += 1
                    logger.debug("중복 스킵 | url=%s", article.url)

        conn.commit()
        logger.info(
            "일괄 저장 완료 | 저장=%d건 / 중복스킵=%d건",
            inserted_count,
            skipped_count,
        )
        return inserted_count, skipped_count

    except psycopg2.Error:
        conn.rollback()
        logger.exception("일괄 저장 실패 - rollback")
        raise
