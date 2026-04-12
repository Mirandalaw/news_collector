"""Price filter application MVP.

DecisionResult.by_symbol_decision을 순회하며
각 종목에 apply_price_filter를 일괄 적용하는 상위 함수.

설계 원칙:
  - apply_price_filter 재사용
  - 가격 입력 계산은 호출자 책임 (이 레이어는 적용만 수행)
  - price input 누락 종목은 예외 없이 pass=False 처리
  - 자동 주문 실행 없음
"""

from __future__ import annotations

from dataclasses import dataclass

from app.signals.decision import DecisionResult
from app.signals.price_filter import PriceFilterInput, PriceFilterResult, apply_price_filter

_MISSING_REASON = "price data missing"


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceFilterApplicationResult:
    """종목 전체에 대한 price filter 일괄 적용 결과.

    Attributes:
        by_symbol: key = 종목 코드, value = PriceFilterResult
    """

    by_symbol: dict[str, PriceFilterResult]

    @property
    def final_candidates(self) -> list[PriceFilterResult]:
        """final_candidate=True인 종목 결과만 반환한다."""
        return [r for r in self.by_symbol.values() if r.final_candidate]


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def apply_price_filters(
    decision: DecisionResult,
    price_inputs: dict[str, PriceFilterInput],
) -> PriceFilterApplicationResult:
    """DecisionResult의 종목별 판단에 price filter를 일괄 적용한다.

    by_symbol_decision에 있는 종목만 처리한다.
    price_inputs에 해당 종목이 없으면 pass=False, final=False로 처리한다.

    Args:
        decision:     make_decision()의 반환값
        price_inputs: 종목별 PriceFilterInput. 호출자가 계산하여 전달.

    Returns:
        PriceFilterApplicationResult — 종목별 PriceFilterResult 포함
    """
    results: dict[str, PriceFilterResult] = {}

    for symbol, news_decision in decision.by_symbol_decision.items():
        price_data = price_inputs.get(symbol)
        if price_data is None:
            results[symbol] = _missing_result(symbol, news_decision)
        else:
            results[symbol] = apply_price_filter(symbol, news_decision, price_data)

    return PriceFilterApplicationResult(by_symbol=results)


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _missing_result(symbol: str, news_decision: str) -> PriceFilterResult:
    """price input이 없는 종목에 대한 기본 결과를 반환한다."""
    return PriceFilterResult(
        symbol=symbol,
        news_decision=news_decision,
        price_filter_pass=False,
        final_candidate=False,
        reason=_MISSING_REASON,
    )
