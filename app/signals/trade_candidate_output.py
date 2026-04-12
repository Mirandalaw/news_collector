"""Trade candidate output MVP.

PriceFilterApplicationResult를 받아
최종 매매 후보를 사람이 읽을 수 있는 형태로 요약한다.

설계 원칙:
  - 계산 로직(price_filter_application)과 출력 로직을 분리
  - 기존 브리핑 구조를 수정하지 않음
  - 자동 주문 실행 없음
  - MVP는 최종 후보 요약까지만
"""

from __future__ import annotations

from dataclasses import dataclass

from app.signals.price_filter_application import PriceFilterApplicationResult

# 정렬 기준: buy_candidate 우선 → sell_candidate → symbol 보조
_DECISION_ORDER: dict[str, int] = {
    "buy_candidate": 0,
    "sell_candidate": 1,
}
_DEFAULT_ORDER = 9


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeCandidateSummary:
    """단일 종목의 최종 매매 후보 요약.

    Attributes:
        symbol:            종목 코드
        news_decision:     뉴스 기반 판단 ("buy_candidate" / "sell_candidate" / "hold")
        price_filter_pass: 가격 조건 통과 여부
        final_candidate:   최종 후보 여부
        reason:            통과/탈락 이유
    """

    symbol: str
    news_decision: str
    price_filter_pass: bool
    final_candidate: bool
    reason: str


@dataclass(frozen=True)
class TradeCandidateReport:
    """전체 매매 후보 요약 보고서.

    Attributes:
        candidates: final_candidate=True 종목 목록 (buy 우선 정렬)
    """

    candidates: list[TradeCandidateSummary]

    @property
    def buy_candidates(self) -> list[TradeCandidateSummary]:
        return [c for c in self.candidates if c.news_decision == "buy_candidate"]

    @property
    def sell_candidates(self) -> list[TradeCandidateSummary]:
        return [c for c in self.candidates if c.news_decision == "sell_candidate"]

    def format_text(self) -> str:
        """사람이 읽을 수 있는 텍스트 요약을 반환한다."""
        if not self.candidates:
            return "최종 매매 후보 없음"

        lines: list[str] = []

        if self.buy_candidates:
            lines.append("[매수 후보]")
            for c in self.buy_candidates:
                lines.append(f"  {c.symbol}  {c.reason}")

        if self.sell_candidates:
            lines.append("[매도 후보]")
            for c in self.sell_candidates:
                lines.append(f"  {c.symbol}  {c.reason}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def build_trade_candidate_report(
    application_result: PriceFilterApplicationResult,
) -> TradeCandidateReport:
    """PriceFilterApplicationResult에서 최종 매매 후보 보고서를 생성한다.

    final_candidate=True 종목만 추출하여
    buy_candidate 우선, 이후 sell_candidate, 동일 판단 내 symbol 순으로 정렬한다.

    Args:
        application_result: apply_price_filters()의 반환값

    Returns:
        TradeCandidateReport — 정렬된 최종 후보 목록 포함
    """
    candidates = [
        TradeCandidateSummary(
            symbol=r.symbol,
            news_decision=r.news_decision,
            price_filter_pass=r.price_filter_pass,
            final_candidate=r.final_candidate,
            reason=r.reason,
        )
        for r in application_result.by_symbol.values()
        if r.final_candidate
    ]

    candidates.sort(key=lambda c: (_DECISION_ORDER.get(c.news_decision, _DEFAULT_ORDER), c.symbol))

    return TradeCandidateReport(candidates=candidates)
