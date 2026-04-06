"""DB 스키마 초기화 모듈.

애플리케이션 시작 시 1회 호출해 테이블과 인덱스를 보장한다.
"""

import logging

import psycopg2.extensions

logger = logging.getLogger(__name__)

_CREATE_TABLE_NEWS_ARTICLES = """
CREATE TABLE IF NOT EXISTS news_articles (
    id           SERIAL       PRIMARY KEY,
    source_name  TEXT         NOT NULL,
    category     TEXT         NOT NULL,
    title        TEXT         NOT NULL,
    url          TEXT         NOT NULL UNIQUE,
    published_at TIMESTAMPTZ,
    summary      TEXT,
    collected_at TIMESTAMPTZ  NOT NULL
);
"""

_CREATE_INDEX_PUBLISHED_AT = """
CREATE INDEX IF NOT EXISTS idx_news_published_at
ON news_articles (published_at DESC);
"""

# title_hash 컬럼: 이미 존재하는 테이블에 안전하게 추가한다.
# 현재는 nullable / 비unique. 추후 중복 제거 정책 강화 시 UNIQUE 제약 추가 가능.
_ADD_COLUMN_TITLE_HASH = """
ALTER TABLE news_articles
ADD COLUMN IF NOT EXISTS title_hash TEXT;
"""

# article_type: 의미 기반 분류 레이블 (market / company / event / general)
# 기존 category(RSS 소스 카테고리)와 구분되는 별도 차원.
_ADD_COLUMN_ARTICLE_TYPE = """
ALTER TABLE news_articles
ADD COLUMN IF NOT EXISTS article_type TEXT NOT NULL DEFAULT 'general';
"""

_CREATE_TABLE_ARTICLE_SYMBOLS = """
CREATE TABLE IF NOT EXISTS article_symbols (
    id         SERIAL      PRIMARY KEY,
    article_id INTEGER     NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    symbol     TEXT        NOT NULL,
    tagged_by  TEXT        NOT NULL,
    tagged_at  TIMESTAMPTZ NOT NULL
);
"""

# (article_id, symbol) 조합 중복 방지 + ON CONFLICT DO NOTHING 지원
_CREATE_UNIQUE_ARTICLE_SYMBOL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_article_symbol
ON article_symbols (article_id, symbol);
"""

# symbol 기준 조회 지원 (특정 종목에 연결된 기사 검색)
_CREATE_INDEX_SYMBOL = """
CREATE INDEX IF NOT EXISTS idx_article_symbols_symbol
ON article_symbols (symbol);
"""


_CREATE_TABLE_JOB_METRICS = """
CREATE TABLE IF NOT EXISTS job_metrics (
    id           SERIAL       PRIMARY KEY,
    job_name     TEXT         NOT NULL,
    started_at   TIMESTAMPTZ  NOT NULL,
    finished_at  TIMESTAMPTZ,
    success      BOOLEAN      NOT NULL,
    elapsed_secs REAL,
    detail       TEXT,
    error_msg    TEXT
);
"""

_CREATE_INDEX_JOB_METRICS_NAME = """
CREATE INDEX IF NOT EXISTS idx_job_metrics_name_started
ON job_metrics (job_name, started_at DESC);
"""


def create_tables(conn: psycopg2.extensions.connection) -> None:
    """모든 테이블과 인덱스를 생성하고 누락 컬럼을 보장한다.

    이미 존재하는 경우 무시한다(IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
    DDL 전체를 단일 트랜잭션으로 처리한다.

    Args:
        conn: psycopg2 커넥션 (autocommit=False 상태여야 함)

    Raises:
        psycopg2.Error: DDL 실행 실패 시 rollback 후 재발생
    """
    try:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_NEWS_ARTICLES)
            cur.execute(_CREATE_INDEX_PUBLISHED_AT)
            cur.execute(_ADD_COLUMN_TITLE_HASH)
            cur.execute(_ADD_COLUMN_ARTICLE_TYPE)
            cur.execute(_CREATE_TABLE_ARTICLE_SYMBOLS)
            cur.execute(_CREATE_UNIQUE_ARTICLE_SYMBOL)
            cur.execute(_CREATE_INDEX_SYMBOL)
            cur.execute(_CREATE_TABLE_JOB_METRICS)
            cur.execute(_CREATE_INDEX_JOB_METRICS_NAME)
        conn.commit()
        logger.info("DB 스키마 초기화 완료 (news_articles, article_symbols, job_metrics)")
    except psycopg2.Error:
        conn.rollback()
        logger.exception("DB 스키마 초기화 실패 - rollback 처리")
        raise
