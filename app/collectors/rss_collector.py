"""RSS 피드 수집 모듈.

RssSource 목록을 받아 feedparser로 기사를 수집하고 NewsArticle 목록을 반환한다.
소스 단위 / 기사 단위 실패는 continue로 처리하며 전체 수집을 중단하지 않는다.
"""

import logging
from dataclasses import dataclass, field

import feedparser

from app.db.repositories.news_repository import NewsArticle
from app.parsers.rss_parser import parse_entry
from app.utils.datetime_utils import now_utc

logger = logging.getLogger(__name__)

# feedparser bozo 예외 중 네트워크/파싱 불가로 판단해 소스 전체를 skip할 유형
_FATAL_BOZO_TYPES: tuple[type[Exception], ...] = (
    OSError,        # 네트워크 오류
    TimeoutError,
)


@dataclass(frozen=True)
class RssSource:
    """단일 RSS 소스 정의."""

    url: str
    source_name: str
    category: str


@dataclass
class CollectionResult:
    """소스별 수집 결과 요약."""

    source_name: str
    collected: int = 0
    skipped: int = 0
    failed: bool = False
    error: str = ""


@dataclass
class CollectionSummary:
    """전체 수집 결과 요약."""

    results: list[CollectionResult] = field(default_factory=list)

    @property
    def total_collected(self) -> int:
        return sum(r.collected for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    @property
    def failed_sources(self) -> list[str]:
        return [r.source_name for r in self.results if r.failed]


def collect_from_source(source: RssSource) -> tuple[list[NewsArticle], CollectionResult]:
    """단일 RSS 소스에서 기사를 수집한다.

    feedparser 파싱 실패 또는 네트워크 오류 시 빈 목록과 failed=True 결과를 반환한다.
    개별 entry 파싱 실패는 skip하고 계속 진행한다.

    Args:
        source: 수집 대상 RSS 소스

    Returns:
        (NewsArticle 목록, CollectionResult) 튜플
    """
    result = CollectionResult(source_name=source.source_name)
    articles: list[NewsArticle] = []

    logger.info("수집 시작 | source=%s | url=%s", source.source_name, source.url)

    try:
        feed = feedparser.parse(source.url)
    except Exception as e:
        result.failed = True
        result.error = str(e)
        logger.error("피드 요청 실패 | source=%s | error=%s", source.source_name, e)
        return articles, result

    # bozo: feedparser가 피드 파싱 중 문제를 감지한 경우
    if feed.bozo:
        bozo_exc = feed.get("bozo_exception")
        if isinstance(bozo_exc, _FATAL_BOZO_TYPES):
            result.failed = True
            result.error = str(bozo_exc)
            logger.error(
                "피드 수집 불가 | source=%s | reason=%s",
                source.source_name,
                bozo_exc,
            )
            return articles, result
        # 부분 파싱 가능한 경우(malformed XML 등)는 경고 후 계속 진행
        if bozo_exc is not None:
            logger.warning(
                "피드 형식 경고 | source=%s | reason=%s",
                source.source_name,
                bozo_exc,
            )

    entries = feed.get("entries", [])
    if not entries:
        logger.warning("수집된 entry 없음 | source=%s", source.source_name)
        return articles, result

    collected_at = now_utc()

    for entry in entries:
        try:
            article = parse_entry(
                entry=entry,
                source_name=source.source_name,
                category=source.category,
                collected_at=collected_at,
            )
        except Exception as e:
            result.skipped += 1
            logger.warning(
                "entry 파싱 실패 - 스킵 | source=%s | error=%s",
                source.source_name,
                e,
            )
            continue

        if article is None:
            result.skipped += 1
            continue

        articles.append(article)
        result.collected += 1

    logger.info(
        "수집 완료 | source=%s | 수집=%d건 / 스킵=%d건",
        source.source_name,
        result.collected,
        result.skipped,
    )

    return articles, result


def collect_all(sources: list[RssSource]) -> tuple[list[NewsArticle], CollectionSummary]:
    """모든 RSS 소스에서 기사를 수집한다.

    소스별 실패는 continue로 처리하고 나머지 소스 수집을 계속한다.

    Args:
        sources: 수집 대상 RssSource 목록

    Returns:
        (전체 NewsArticle 목록, CollectionSummary) 튜플
    """
    all_articles: list[NewsArticle] = []
    summary = CollectionSummary()

    logger.info("전체 수집 시작 | 소스 수=%d", len(sources))

    for source in sources:
        try:
            articles, result = collect_from_source(source)
        except Exception as e:
            # collect_from_source 자체가 예상치 못한 예외를 던진 경우
            failed_result = CollectionResult(
                source_name=source.source_name,
                failed=True,
                error=str(e),
            )
            summary.results.append(failed_result)
            logger.error(
                "소스 처리 중 예외 발생 - 건너뜀 | source=%s | error=%s",
                source.source_name,
                e,
            )
            continue

        all_articles.extend(articles)
        summary.results.append(result)

    logger.info(
        "전체 수집 종료 | 총 수집=%d건 / 총 스킵=%d건 / 실패 소스=%s",
        summary.total_collected,
        summary.total_skipped,
        summary.failed_sources or "없음",
    )

    return all_articles, summary
