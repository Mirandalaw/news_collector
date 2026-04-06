"""아침 브리핑 조회 서비스.

BriefingService.run(query) → BriefingResult 흐름으로
market_news / symbol_news / event_news 세 섹션을 조회한다.
"""

import dataclasses
import logging
from dataclasses import dataclass, field
from datetime import datetime

import psycopg2

from app.db.connection import DatabaseConfig, managed_connection
from app.db.repositories.briefing_repository import (
    BriefingArticle,
    fetch_event_news,
    fetch_market_news,
    fetch_symbol_news,
)
from app.summarizers.base import Summarizer, SummaryRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 입력 파라미터
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BriefingQuery:
    """브리핑 조회 파라미터.

    Attributes:
        since: 조회 시작 시각 (UTC, inclusive)
        until: 조회 종료 시각 (UTC, exclusive)
        symbols: 관심 종목 코드 목록. 빈 리스트면 전체 태깅 기사.
        market_limit: market_news 최대 건수
        symbol_limit: symbol_news 최대 건수
        event_limit: event_news 최대 건수
    """

    since: datetime
    until: datetime
    symbols: list[str] = field(default_factory=list)
    market_limit: int = 20
    symbol_limit: int = 30
    event_limit: int = 10


# ---------------------------------------------------------------------------
# 결과 구조
# ---------------------------------------------------------------------------


@dataclass
class BriefingResult:
    """브리핑 조회 결과.

    세 섹션은 독립적으로 조회되며, 섹션 간 중복이 있을 수 있다.
    deduplicated_symbol_news property를 통해 market_news와 겹치지 않는
    symbol_news를 얻을 수 있다.
    """

    query: BriefingQuery
    market_news: list[BriefingArticle]
    symbol_news: list[BriefingArticle]
    event_news: list[BriefingArticle]

    @property
    def deduplicated_symbol_news(self) -> list[BriefingArticle]:
        """market_news에 이미 포함된 기사를 제외한 symbol_news.

        market + symbol 양쪽에 등장하는 기사를 symbol 섹션에서 제거해
        브리핑 소비자에게 중복 없는 뷰를 제공한다.
        """
        market_ids = {a.id for a in self.market_news}
        return [a for a in self.symbol_news if a.id not in market_ids]

    def log_summary(self) -> None:
        logger.info(
            "[ 브리핑 조회 완료 ] since=%s | market=%d건 / symbol=%d건 / event=%d건",
            self.query.since.strftime("%Y-%m-%d %H:%M UTC"),
            len(self.market_news),
            len(self.symbol_news),
            len(self.event_news),
        )
        _log_section("market", self.market_news)
        _log_section("symbol", self.symbol_news)
        _log_section("event", self.event_news)

    def to_dict(self) -> dict:
        """직렬화 가능한 dict로 변환한다. JSON 출력 / 디버깅용."""
        return {
            "since": self.query.since.isoformat(),
            "until": self.query.until.isoformat(),
            "market_news": [_article_to_dict(a) for a in self.market_news],
            "symbol_news": [_article_to_dict(a) for a in self.symbol_news],
            "event_news": [_article_to_dict(a) for a in self.event_news],
        }


# ---------------------------------------------------------------------------
# 서비스
# ---------------------------------------------------------------------------


class BriefingService:
    """아침 브리핑 조회 파이프라인.

    Args:
        db_config: PostgreSQL 접속 설정
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        summarizer: Summarizer | None = None,
    ) -> None:
        self._db_config = db_config
        self._summarizer = summarizer

    def run(self, query: BriefingQuery) -> BriefingResult:
        """세 섹션을 단일 커넥션으로 조회하고 BriefingResult를 반환한다.

        Args:
            query: 조회 파라미터 (시간 범위, 관심 종목, 섹션별 limit)

        Returns:
            BriefingResult

        Raises:
            psycopg2.OperationalError: DB 접속 실패 시
        """
        logger.info(
            "브리핑 조회 시작 | since=%s ~ until=%s | symbols=%d개",
            query.since.strftime("%Y-%m-%d %H:%M"),
            query.until.strftime("%Y-%m-%d %H:%M"),
            len(query.symbols),
        )

        try:
            with managed_connection(self._db_config) as conn:
                market_news = fetch_market_news(conn, query.since, query.until, query.market_limit)
                symbol_news = fetch_symbol_news(
                    conn,
                    query.since,
                    query.until,
                    symbols=query.symbols or None,
                    limit=query.symbol_limit,
                )
                event_news = fetch_event_news(conn, query.since, query.until, query.event_limit)
        except psycopg2.Error:
            logger.exception("브리핑 조회 실패")
            raise

        # 요약기가 주입된 경우 섹션별 일괄 요약 적용
        if self._summarizer is not None:
            market_news = _apply_summarizer(self._summarizer, market_news)
            symbol_news = _apply_summarizer(self._summarizer, symbol_news)
            event_news = _apply_summarizer(self._summarizer, event_news)
            logger.info(
                "요약 완료 | provider=%s | market=%d / symbol=%d / event=%d",
                self._summarizer.provider_name,
                len(market_news),
                len(symbol_news),
                len(event_news),
            )

        result = BriefingResult(
            query=query,
            market_news=market_news,
            symbol_news=symbol_news,
            event_news=event_news,
        )
        result.log_summary()
        return result


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _apply_summarizer(
    summarizer: Summarizer,
    articles: list[BriefingArticle],
) -> list[BriefingArticle]:
    """기사 목록에 요약기를 적용해 ai_summary 필드가 채워진 새 목록을 반환한다."""
    if not articles:
        return articles
    requests = [
        SummaryRequest(
            title=a.title,
            body=a.summary,
            source_name=a.source_name,
            article_type=a.article_type,
            symbols=a.symbols,
        )
        for a in articles
    ]
    responses = summarizer.summarize_batch(requests)
    return [dataclasses.replace(a, ai_summary=r.text) for a, r in zip(articles, responses)]


def _log_section(name: str, articles: list[BriefingArticle]) -> None:
    if not articles:
        logger.info("  [%s] 결과 없음", name)
        return
    for a in articles:
        sym_str = f" [{','.join(a.symbols)}]" if a.symbols else ""
        logger.info(
            "  [%s]%s %s | %s",
            name,
            sym_str,
            a.title[:60],
            a.source_name,
        )


def _article_to_dict(a: BriefingArticle) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "url": a.url,
        "source_name": a.source_name,
        "summary": a.summary,
        "article_type": a.article_type,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "collected_at": a.collected_at.isoformat(),
        "symbols": a.symbols,
        "ai_summary": a.ai_summary,
    }
