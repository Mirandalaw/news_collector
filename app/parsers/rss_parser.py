"""RSS feedparser entry 파싱 및 데이터 정제 모듈.

feedparser entry 객체를 받아 NewsArticle로 변환한다.
필수 필드 누락 또는 파싱 불가 항목은 None을 반환해 호출자가 skip하도록 한다.
"""

import logging
import re
from datetime import datetime

from app.db.repositories.news_repository import NewsArticle
from app.utils.datetime_utils import now_utc, parse_struct_time_to_utc
from app.utils.hashing import compute_title_hash

logger = logging.getLogger(__name__)

# feedparser FeedParserDict entry의 타입 alias (런타임에는 dict-like 객체)
type FeedEntry = object

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def parse_entry(
    entry: FeedEntry,
    source_name: str,
    category: str,
    collected_at: datetime | None = None,
) -> NewsArticle | None:
    """feedparser entry 1건을 NewsArticle로 변환한다.

    필수 필드(title, url)가 없거나 빈 문자열이면 None을 반환한다.

    Args:
        entry: feedparser가 반환한 entry 객체
        source_name: RSS 소스 이름 (예: "한국경제")
        category: 기사 카테고리 (예: "경제")
        collected_at: 수집 시각. None이면 현재 UTC 시각 사용.

    Returns:
        NewsArticle 인스턴스. 필수 필드 누락 시 None.
    """
    title = _extract_text(entry, "title")
    url = _extract_text(entry, "link")

    if not title:
        logger.debug("title 누락 - 스킵 | source=%s", source_name)
        return None

    if not url:
        logger.debug("url 누락 - 스킵 | source=%s | title=%.40r", source_name, title)
        return None

    published_at = parse_struct_time_to_utc(getattr(entry, "published_parsed", None))

    summary = _extract_summary(entry)

    return NewsArticle(
        source_name=source_name,
        category=category,
        title=title,
        url=url,
        published_at=published_at,
        summary=summary,
        collected_at=collected_at or now_utc(),
        title_hash=compute_title_hash(title),
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _extract_text(entry: FeedEntry, field: str) -> str:
    """entry에서 문자열 필드를 안전하게 추출하고 공백을 정규화한다."""
    raw: str = getattr(entry, field, "") or ""
    return _normalize_whitespace(raw.strip())


def _extract_summary(entry: FeedEntry) -> str:
    """summary 또는 description 필드를 추출하고 HTML 태그를 제거한다.

    feedparser는 summary와 description을 모두 제공할 수 있다.
    summary를 우선하고 없으면 description을 사용한다.
    둘 다 없으면 빈 문자열을 반환한다.
    """
    raw: str = (
        getattr(entry, "summary", "")
        or getattr(entry, "description", "")
        or ""
    )
    cleaned = _strip_html(raw)
    return _normalize_whitespace(cleaned).strip()


def _strip_html(text: str) -> str:
    """HTML 태그와 엔티티를 제거한다."""
    text = _HTML_TAG_PATTERN.sub(" ", text)
    # 자주 등장하는 HTML 엔티티 처리
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    return text


def _normalize_whitespace(text: str) -> str:
    """연속된 공백/줄바꿈을 단일 공백으로 정규화한다."""
    return _WHITESPACE_PATTERN.sub(" ", text).strip()
