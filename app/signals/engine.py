"""시그널 엔진.

BriefingResult를 입력받아 모든 규칙을 실행하고 SignalReport를 반환한다.

설계 원칙:
  - 엔진은 규칙의 내용을 모른다 (Protocol 의존)
  - 규칙 평가는 독립적 (한 규칙의 실패가 다른 규칙에 영향 없음)
  - 한 기사에 여러 규칙이 동시 발동 가능 (의도적 설계)
  - 중복 시그널 제거: (article_id, rule_name) 쌍이 동일하면 1개만 유지
"""

import logging
from datetime import datetime, timezone

from app.db.repositories.briefing_repository import BriefingArticle
from app.services.briefing_service import BriefingResult
from app.signals.models import Signal, SignalReport
from app.signals.rules.base import SignalRule
from app.signals.rules.registry import DEFAULT_RULES

logger = logging.getLogger(__name__)


class SignalEngine:
    """뉴스 브리핑에 시그널 규칙을 적용하는 엔진.

    Args:
        rules: 사용할 SignalRule 목록. None이면 DEFAULT_RULES 사용.
    """

    def __init__(self, rules: list[SignalRule] | None = None) -> None:
        self._rules = rules if rules is not None else DEFAULT_RULES

    def analyze(self, result: BriefingResult) -> SignalReport:
        """BriefingResult 전체를 분석하고 SignalReport를 반환한다.

        Args:
            result: BriefingService.run()의 반환값

        Returns:
            SignalReport — 감지된 시그널 전체 포함
        """
        articles = _collect_unique(result)
        logger.info(
            "시그널 분석 시작 | 기사=%d건 | 규칙=%d개",
            len(articles),
            len(self._rules),
        )

        signals = self._run_rules(articles)

        logger.info(
            "시그널 분석 완료 | 시그널=%d건 (bullish=%d / bearish=%d / neutral=%d / mixed=%d)",
            len(signals),
            sum(1 for s in signals if s.direction.value == "bullish"),
            sum(1 for s in signals if s.direction.value == "bearish"),
            sum(1 for s in signals if s.direction.value == "neutral"),
            sum(1 for s in signals if s.direction.value == "mixed"),
        )

        return SignalReport(
            analyzed_at=datetime.now(timezone.utc),
            briefing_since=result.query.since,
            briefing_until=result.query.until,
            signals=signals,
            analyzed_count=len(articles),
        )

    def _run_rules(self, articles: list[BriefingArticle]) -> list[Signal]:
        """모든 기사 × 모든 규칙을 실행하고 중복 없는 시그널 목록을 반환한다."""
        seen: set[tuple[int, str]] = set()  # (article_id, rule_name)
        signals: list[Signal] = []

        for article in articles:
            for rule in self._rules:
                try:
                    signal = rule.evaluate(article)
                except Exception:
                    logger.warning(
                        "규칙 평가 예외 무시 | rule=%s | article_id=%d",
                        rule.rule_name,
                        article.id,
                        exc_info=True,
                    )
                    continue

                if signal is None:
                    continue

                key = (signal.article_id, signal.rule_name)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(signal)

        # 중요도(HIGH→LOW) → 방향(bullish→bearish→mixed→neutral) 순 정렬
        importance_order = {"high": 0, "medium": 1, "low": 2}
        direction_order = {"bullish": 0, "bearish": 1, "mixed": 2, "neutral": 3}
        signals.sort(
            key=lambda s: (
                importance_order.get(s.importance.value, 9),
                direction_order.get(s.direction.value, 9),
            )
        )
        return signals


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _collect_unique(result: BriefingResult) -> list[BriefingArticle]:
    """세 섹션에서 중복 없는 기사 목록을 수집한다."""
    seen: set[int] = set()
    unique: list[BriefingArticle] = []
    for article in result.market_news + result.symbol_news + result.event_news:
        if article.id not in seen:
            seen.add(article.id)
            unique.append(article)
    return unique
