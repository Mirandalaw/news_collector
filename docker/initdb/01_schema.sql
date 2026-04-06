-- ============================================================
-- news_collector DB 스키마 자동 초기화
-- Postgres 컨테이너가 빈 데이터 디렉토리로 처음 시작할 때만 실행된다.
-- (이미 데이터가 있는 컨테이너 재시작에는 실행되지 않음)
-- ============================================================

-- news_articles
CREATE TABLE IF NOT EXISTS news_articles (
    id           SERIAL       PRIMARY KEY,
    source_name  TEXT         NOT NULL,
    category     TEXT         NOT NULL,
    title        TEXT         NOT NULL,
    url          TEXT         NOT NULL UNIQUE,
    published_at TIMESTAMPTZ,
    summary      TEXT,
    collected_at TIMESTAMPTZ  NOT NULL,
    title_hash   TEXT,
    article_type TEXT         NOT NULL DEFAULT 'general'
);

CREATE INDEX IF NOT EXISTS idx_news_published_at
    ON news_articles (published_at DESC);

-- article_symbols
CREATE TABLE IF NOT EXISTS article_symbols (
    id         SERIAL      PRIMARY KEY,
    article_id INTEGER     NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    symbol     TEXT        NOT NULL,
    tagged_by  TEXT        NOT NULL,
    tagged_at  TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_article_symbol
    ON article_symbols (article_id, symbol);

CREATE INDEX IF NOT EXISTS idx_article_symbols_symbol
    ON article_symbols (symbol);

-- job_metrics
CREATE TABLE IF NOT EXISTS job_metrics (
    id           SERIAL      PRIMARY KEY,
    job_name     TEXT        NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    success      BOOLEAN     NOT NULL,
    elapsed_secs REAL,
    detail       TEXT,
    error_msg    TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_metrics_name_started
    ON job_metrics (job_name, started_at DESC);
