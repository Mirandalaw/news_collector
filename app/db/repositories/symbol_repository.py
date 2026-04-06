"""article_symbols 테이블 대상 데이터 접근 모듈.

기사와 종목 코드의 N:M 연결을 관리한다.
"""

import logging
from datetime import datetime

import psycopg2.extensions

from app.utils.datetime_utils import now_utc

logger = logging.getLogger(__name__)

_INSERT_ARTICLE_SYMBOL = """
INSERT INTO article_symbols (article_id, symbol, tagged_by, tagged_at)
VALUES (%(article_id)s, %(symbol)s, %(tagged_by)s, %(tagged_at)s)
ON CONFLICT (article_id, symbol) DO NOTHING;
"""

_SELECT_IDS_BY_URLS = """
SELECT id, url
FROM news_articles
WHERE url = ANY(%s);
"""


def fetch_article_ids_by_urls(
    conn: psycopg2.extensions.connection,
    urls: list[str],
) -> dict[str, int]:
    """URL 목록으로 article_id를 조회해 {url: id} 딕셔너리를 반환한다.

    DB에 없는 URL은 결과에 포함되지 않는다.
    INSERT 후 ID를 얻기 위해 사용한다. (RETURNING 없이 URL이 이미 UNIQUE임을 이용)

    Args:
        conn: psycopg2 커넥션
        urls: 조회할 URL 목록

    Returns:
        {url: article_id} 딕셔너리. 조회 결과가 없으면 빈 딕셔너리.

    Raises:
        psycopg2.Error: DB 조회 실패 시
    """
    if not urls:
        return {}

    with conn.cursor() as cur:
        cur.execute(_SELECT_IDS_BY_URLS, [urls])
        return {url: article_id for article_id, url in cur.fetchall()}


def insert_article_symbols(
    conn: psycopg2.extensions.connection,
    article_id: int,
    symbols: list[str],
    tagged_by: str,
    tagged_at: datetime | None = None,
) -> int:
    """기사 1건에 대한 종목 태그를 일괄 삽입한다.

    이미 존재하는 (article_id, symbol) 조합은 skip한다.
    트랜잭션은 호출자가 관리한다 (commit 없음).

    Args:
        conn: psycopg2 커넥션
        article_id: 태깅 대상 기사 ID
        symbols: 종목 코드 목록
        tagged_by: 분류기 이름 (예: 'keyword', 'ai')
        tagged_at: 태깅 시각. None이면 현재 UTC 시각 사용.

    Returns:
        실제 삽입된 태그 수 (중복 제외)

    Raises:
        psycopg2.Error: DB 오류 발생 시
    """
    if not symbols:
        return 0

    ts = tagged_at or now_utc()
    inserted = 0

    with conn.cursor() as cur:
        for symbol in symbols:
            cur.execute(
                _INSERT_ARTICLE_SYMBOL,
                {
                    "article_id": article_id,
                    "symbol": symbol,
                    "tagged_by": tagged_by,
                    "tagged_at": ts,
                },
            )
            if cur.rowcount == 1:
                inserted += 1

    return inserted
