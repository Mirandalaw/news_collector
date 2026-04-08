"""아침 브리핑용 뉴스 조회 모듈.

읽기 전용 쿼리만 포함한다. 트랜잭션/커밋 없음.

BriefingArticle: 조회 전용 DTO (NewsArticle과 별도).
  - symbols 필드 포함 (symbol_news 섹션에서 사용)
  - 쓰기 모델과 읽기 모델을 분리해 각 레이어의 책임을 명확히 한다.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import psycopg2.extensions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BriefingArticle:
    """브리핑 조회 결과 단위 DTO.

    Attributes:
        id: DB primary key
        title: 기사 제목
        url: 원문 URL
        source_name: 뉴스 소스명
        summary: 기사 요약 (없으면 빈 문자열)
        article_type: 의미 분류 (market / company / event / general)
        published_at: 기사 발행 시각 (없을 수 있음)
        collected_at: 수집 시각
        symbols: 매칭된 종목 코드 목록 (symbol_news 아닌 경우 빈 리스트)
        ai_summary: LLM 요약 결과. 요약기 미주입 시 빈 문자열.
        title_hash: SHA-256(normalize(title)). 빈 문자열 = 미계산.
    """

    id: int
    title: str
    url: str
    source_name: str
    summary: str
    article_type: str
    published_at: datetime | None
    collected_at: datetime
    symbols: list[str] = field(default_factory=list)
    ai_summary: str = ""  # LLM 요약 결과. 요약기 미주입 시 빈 문자열.
    title_hash: str = ""  # 그룹핑 기준. 빈 문자열 = 미계산 → 단독 그룹.


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# 정렬: published_at 우선, NULL이면 collected_at 폴백 → 최신순
_ORDER_BY = "ORDER BY COALESCE(a.published_at, a.collected_at) DESC"

_SELECT_MARKET_NEWS = f"""
SELECT
    a.id,
    a.title,
    a.url,
    a.source_name,
    COALESCE(a.summary, '')  AS summary,
    a.article_type,
    a.published_at,
    a.collected_at,
    COALESCE(a.title_hash, '') AS title_hash
FROM news_articles a
WHERE a.article_type = 'market'
  AND a.collected_at >= %(since)s
  AND a.collected_at <  %(until)s
{_ORDER_BY.replace("a.", "a.")}
LIMIT %(limit)s;
"""

_SELECT_EVENT_NEWS = f"""
SELECT
    a.id,
    a.title,
    a.url,
    a.source_name,
    COALESCE(a.summary, '')  AS summary,
    a.article_type,
    a.published_at,
    a.collected_at,
    COALESCE(a.title_hash, '') AS title_hash
FROM news_articles a
WHERE a.article_type = 'event'
  AND a.collected_at >= %(since)s
  AND a.collected_at <  %(until)s
{_ORDER_BY.replace("a.", "a.")}
LIMIT %(limit)s;
"""

# symbol_news: 종목 태그가 달린 기사 전체 (article_type 무관)
# GROUP BY로 기사당 1행 보장, array_agg로 모든 매칭 종목을 하나의 행에 포함
# row[8] = symbols, row[9] = title_hash
_SELECT_SYMBOL_NEWS_ALL = f"""
SELECT
    a.id,
    a.title,
    a.url,
    a.source_name,
    COALESCE(a.summary, '')                         AS summary,
    a.article_type,
    a.published_at,
    a.collected_at,
    array_agg(DISTINCT s.symbol ORDER BY s.symbol)  AS symbols,
    COALESCE(a.title_hash, '')                      AS title_hash
FROM news_articles a
JOIN article_symbols s ON a.id = s.article_id
WHERE a.collected_at >= %(since)s
  AND a.collected_at <  %(until)s
GROUP BY a.id, a.title, a.url, a.source_name, a.summary,
         a.article_type, a.published_at, a.collected_at, a.title_hash
{_ORDER_BY}
LIMIT %(limit)s;
"""

# 관심 종목 목록으로 필터링된 symbol_news
# row[8] = symbols, row[9] = title_hash
_SELECT_SYMBOL_NEWS_FILTERED = f"""
SELECT
    a.id,
    a.title,
    a.url,
    a.source_name,
    COALESCE(a.summary, '')                         AS summary,
    a.article_type,
    a.published_at,
    a.collected_at,
    array_agg(DISTINCT s.symbol ORDER BY s.symbol)  AS symbols,
    COALESCE(a.title_hash, '')                      AS title_hash
FROM news_articles a
JOIN article_symbols s ON a.id = s.article_id
WHERE a.collected_at >= %(since)s
  AND a.collected_at <  %(until)s
  AND s.symbol = ANY(%(symbols)s)
GROUP BY a.id, a.title, a.url, a.source_name, a.summary,
         a.article_type, a.published_at, a.collected_at, a.title_hash
{_ORDER_BY}
LIMIT %(limit)s;
"""


# ---------------------------------------------------------------------------
# 조회 함수
# ---------------------------------------------------------------------------


def fetch_market_news(
    conn: psycopg2.extensions.connection,
    since: datetime,
    until: datetime,
    limit: int = 20,
) -> list[BriefingArticle]:
    """시장/거시경제 뉴스를 조회한다.

    article_type = 'market' 인 기사를 최신순으로 반환한다.

    Args:
        conn: psycopg2 커넥션 (읽기 전용 사용)
        since: 조회 시작 시각 (inclusive)
        until: 조회 종료 시각 (exclusive)
        limit: 최대 반환 건수

    Returns:
        BriefingArticle 목록. 결과가 없으면 빈 리스트.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_MARKET_NEWS, {"since": since, "until": until, "limit": limit})
        rows = cur.fetchall()

    result = [_row_to_article(row, symbols=[]) for row in rows]
    logger.debug("fetch_market_news | 조회=%d건 | since=%s", len(result), since.isoformat())
    return result


def fetch_event_news(
    conn: psycopg2.extensions.connection,
    since: datetime,
    until: datetime,
    limit: int = 10,
) -> list[BriefingArticle]:
    """이벤트/일정 뉴스를 조회한다.

    article_type = 'event' 인 기사를 최신순으로 반환한다.

    Args:
        conn: psycopg2 커넥션
        since: 조회 시작 시각 (inclusive)
        until: 조회 종료 시각 (exclusive)
        limit: 최대 반환 건수

    Returns:
        BriefingArticle 목록. 결과가 없으면 빈 리스트.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_EVENT_NEWS, {"since": since, "until": until, "limit": limit})
        rows = cur.fetchall()

    result = [_row_to_article(row, symbols=[]) for row in rows]
    logger.debug("fetch_event_news | 조회=%d건 | since=%s", len(result), since.isoformat())
    return result


def fetch_symbol_news(
    conn: psycopg2.extensions.connection,
    since: datetime,
    until: datetime,
    symbols: list[str] | None = None,
    limit: int = 30,
) -> list[BriefingArticle]:
    """관심 종목 관련 뉴스를 조회한다.

    article_symbols 테이블과 JOIN해 종목 태그가 달린 기사를 반환한다.
    기사당 1행이 보장되며, 매칭된 모든 종목 코드가 symbols 필드에 포함된다.

    Args:
        conn: psycopg2 커넥션
        since: 조회 시작 시각 (inclusive)
        until: 조회 종료 시각 (exclusive)
        symbols: 필터링할 종목 코드 목록.
                 None 또는 빈 리스트이면 태그가 달린 모든 기사를 반환한다.
        limit: 최대 반환 건수

    Returns:
        BriefingArticle 목록 (symbols 필드 포함). 결과가 없으면 빈 리스트.
    """
    with conn.cursor() as cur:
        if symbols:
            cur.execute(
                _SELECT_SYMBOL_NEWS_FILTERED,
                {"since": since, "until": until, "symbols": symbols, "limit": limit},
            )
        else:
            cur.execute(
                _SELECT_SYMBOL_NEWS_ALL,
                {"since": since, "until": until, "limit": limit},
            )
        rows = cur.fetchall()

    result = [_row_to_symbol_article(row) for row in rows]
    logger.debug(
        "fetch_symbol_news | 조회=%d건 | symbols=%s | since=%s",
        len(result),
        symbols,
        since.isoformat(),
    )
    return result


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _row_to_article(row: tuple, symbols: list[str]) -> BriefingArticle:
    """market/event 쿼리 row를 BriefingArticle로 변환한다.

    row 인덱스:
      0=id, 1=title, 2=url, 3=source_name, 4=summary, 5=article_type,
      6=published_at, 7=collected_at, 8=title_hash
    """
    logger.debug(
        "_row_to_article | row_len=%d | row[8]=%r", len(row), row[8] if len(row) > 8 else "MISSING"
    )
    return BriefingArticle(
        id=row[0],
        title=row[1],
        url=row[2],
        source_name=row[3],
        summary=row[4],
        article_type=row[5],
        published_at=row[6],
        collected_at=row[7],
        symbols=symbols,
        title_hash=row[8] if len(row) > 8 else "",
    )


def _row_to_symbol_article(row: tuple) -> BriefingArticle:
    """DB 행(id~title_hash 10열)을 BriefingArticle로 변환.

    symbol 쿼리 row 인덱스:
      0=id, 1=title, 2=url, 3=source_name, 4=summary, 5=article_type,
      6=published_at, 7=collected_at, 8=symbols, 9=title_hash
    """
    logger.debug(
        "_row_to_symbol_article | row_len=%d | row[9]=%r",
        len(row),
        row[9] if len(row) > 9 else "MISSING",
    )
    return BriefingArticle(
        id=row[0],
        title=row[1],
        url=row[2],
        source_name=row[3],
        summary=row[4],
        article_type=row[5],
        published_at=row[6],
        collected_at=row[7],
        symbols=list(row[8]) if row[8] else [],
        title_hash=row[9] if len(row) > 9 else "",
    )
