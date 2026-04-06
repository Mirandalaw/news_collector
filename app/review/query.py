"""검수용 기사 조회 쿼리 모듈.

브리핑 조회(fetch_market_news 등)와 달리 article_type 필터 없이
수집 윈도우 내 전체 기사를 조회한다. title_hash도 함께 반환한다.
"""

import logging
from datetime import datetime

import psycopg2.extensions

from app.review.models import ReviewArticle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# LEFT JOIN: 종목 태그가 없는 기사도 포함 (article_symbols 미존재 행)
# array_remove(..., NULL): LEFT JOIN 시 심볼이 없으면 NULL이 들어오므로 제거
_SELECT_ALL_ARTICLES = """
SELECT
    a.id,
    a.title,
    a.url,
    a.source_name,
    COALESCE(a.summary, '')                                  AS summary,
    a.article_type,
    a.published_at,
    a.collected_at,
    COALESCE(a.title_hash, '')                               AS title_hash,
    array_remove(array_agg(DISTINCT s.symbol), NULL)         AS symbols
FROM news_articles a
LEFT JOIN article_symbols s ON a.id = s.article_id
WHERE a.collected_at >= %(since)s
  AND a.collected_at <  %(until)s
GROUP BY a.id, a.title, a.url, a.source_name, a.summary,
         a.article_type, a.published_at, a.collected_at, a.title_hash
ORDER BY COALESCE(a.published_at, a.collected_at) DESC
LIMIT %(limit)s;
"""


# ---------------------------------------------------------------------------
# 조회 함수
# ---------------------------------------------------------------------------


def fetch_all_articles(
    conn: psycopg2.extensions.connection,
    since: datetime,
    until: datetime,
    limit: int = 500,
) -> list[ReviewArticle]:
    """검수 대상 전체 기사를 조회한다.

    브리핑 조회와 달리 article_type 필터 없이 모든 기사를 반환한다.
    LEFT JOIN으로 symbol 태그가 없는 기사도 포함된다.

    Args:
        conn:  psycopg2 커넥션 (읽기 전용 사용)
        since: 수집 시각 기준 시작 (inclusive)
        until: 수집 시각 기준 종료 (exclusive)
        limit: 최대 반환 건수 (기본 500)

    Returns:
        ReviewArticle 목록. 최신순 정렬.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_ALL_ARTICLES, {"since": since, "until": until, "limit": limit})
        rows = cur.fetchall()

    result = [_row_to_review_article(row) for row in rows]
    logger.debug(
        "fetch_all_articles | 조회=%d건 | since=%s ~ until=%s",
        len(result),
        since.isoformat(),
        until.isoformat(),
    )
    return result


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _row_to_review_article(row: tuple) -> ReviewArticle:
    """쿼리 결과 행을 ReviewArticle로 변환한다.

    컬럼 순서: id, title, url, source_name, summary, article_type,
               published_at, collected_at, title_hash, symbols
    """
    return ReviewArticle(
        id=row[0],
        title=row[1],
        url=row[2],
        source_name=row[3],
        summary=row[4],
        article_type=row[5],
        published_at=row[6],
        collected_at=row[7],
        title_hash=row[8],
        symbols=list(row[9]) if row[9] else [],
    )
