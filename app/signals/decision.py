"""Signal decision MVP.

집계된 시장/종목 점수를 해석하여 매매 판단 후보를 반환하는 순수 함수.

설계 원칙:
  - 점수 계산(scoring) 및 집계(aggregation)와 판단 해석(decision)을 분리
  - 단순 규칙 기반, 설명 가능한 구조 유지
  - 자동 주문 실행 없음
  - 차트/가격 조건과의 결합은 다음 단계
"""

from __future__ import annotations

from dataclasses import dataclass

from app.signals.aggregation import AggregationResult
from app.signals.scoring import ScoreResult

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_BUY_THRESHOLD = 3
_SELL_THRESHOLD = -3


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionResult:
    """시장 및 종목 단위 매매 판단 결과.

    Attributes:
        market_bias:        시장 방향성 판단 ("bullish_bias" / "bearish_bias" / "neutral_bias")
        by_symbol_decision: 종목별 판단. key = 종목 코드,
                            value = "buy_candidate" / "sell_candidate" / "hold"
    """

    market_bias: str
    by_symbol_decision: dict[str, str]


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def make_decision(aggregation: AggregationResult) -> DecisionResult:
    """AggregationResult를 해석하여 시장 bias와 종목별 판단을 반환한다.

    Args:
        aggregation: aggregate_signals()의 반환값

    Returns:
        DecisionResult — market_bias와 by_symbol_decision 포함
    """
    return DecisionResult(
        market_bias=_interpret_market(aggregation.market_score),
        by_symbol_decision={
            sym: _interpret_symbol(score) for sym, score in aggregation.by_symbol.items()
        },
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _interpret_market(score: ScoreResult) -> str:
    """시장 점수를 bias 문자열로 변환한다."""
    if score.total_score >= _BUY_THRESHOLD:
        return "bullish_bias"
    if score.total_score <= _SELL_THRESHOLD:
        return "bearish_bias"
    return "neutral_bias"


def _interpret_symbol(score: ScoreResult) -> str:
    """종목 점수를 매매 판단 문자열로 변환한다."""
    if score.total_score >= _BUY_THRESHOLD:
        return "buy_candidate"
    if score.total_score <= _SELL_THRESHOLD:
        return "sell_candidate"
    return "hold"
