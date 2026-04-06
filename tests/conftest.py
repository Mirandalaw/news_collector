"""공유 픽스처.

- now_utc: 테스트용 고정 datetime
- make_article: 최소 필드만 지정해 NewsArticle 생성
- db_conn: 실제 DB 연결 (통합 테스트 전용, @pytest.mark.integration 으로 분리)
"""

import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.db.repositories.news_repository import NewsArticle
from app.utils.hashing import compute_title_hash


# ---------------------------------------------------------------------------
# 공통 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def fixed_now() -> datetime:
    """재현 가능한 고정 UTC datetime."""
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def make_article(fixed_now):
    """최소 필드로 NewsArticle을 생성하는 팩토리 픽스처."""

    def _factory(
        title: str = "기본 타이틀",
        url: str = "https://example.com/1",
        source_name: str = "테스트소스",
        category: str = "경제",
        title_hash: str | None = None,
    ) -> NewsArticle:
        return NewsArticle(
            source_name=source_name,
            category=category,
            title=title,
            url=url,
            collected_at=fixed_now,
            title_hash=title_hash if title_hash is not None else compute_title_hash(title),
        )

    return _factory


def make_feed_entry(**kwargs) -> SimpleNamespace:
    """feedparser entry를 흉내내는 SimpleNamespace 객체.

    parse_entry가 사용하는 속성의 기본값을 제공하고 kwargs로 덮어쓴다.
    getattr(entry, field, default) 패턴과 완전히 호환된다.
    """
    defaults = {
        "title": "기본 타이틀",
        "link": "https://example.com/1",
        "published_parsed": None,
        "summary": "",
        "description": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# 통합 테스트 전용 픽스처 (실제 DB 연결)
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: 실제 DB가 필요한 통합 테스트")


@pytest.fixture(scope="session")
def db_conn():
    """실제 PostgreSQL 커넥션. @pytest.mark.integration 테스트에서만 사용.

    환경변수가 없으면 로컬 기본값(DB_USER=현재 OS 유저)을 사용한다.
    """
    pytest.importorskip("psycopg2")
    from app.db.connection import DatabaseConfig, get_connection
    from app.db.schema import create_tables

    config = DatabaseConfig.from_env()
    conn = get_connection(config)
    create_tables(conn)
    yield conn
    conn.close()
