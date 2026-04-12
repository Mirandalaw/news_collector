"""Signal scoring MVP.

Signal 리스트를 받아 점수를 계산하고 매매 판단 결과를 반환하는 순수 함수.

설계 원칙:
  - 규칙 기반, 설명 가능한 단순 구조 유지
  - 종목/시장 단위 집계는 이 모듈의 책임이 아님 (호출자가 분리해서 전달)
  - 차트/가격 필터와의 결합은 다음 단계
"""

from __future__ import annotations

from dataclasses import dataclass

from app.signals.models import Direction, Importance, Signal

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_IMPORTANCE_WEIGHT: dict[Importance, int] = {
    Importance.HIGH: 3,
    Importance.MEDIUM: 2,
    Importance.LOW: 1,
}

_BUY_THRESHOLD = 3
_SELL_THRESHOLD = -3


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreResult:
    """Signal 목록에 대한 점수 계산 결과.

    Attributes:
        total_score:        가중합 점수 (bullish → +weight, bearish → -weight)
        bullish_count:      bullish signal 수
        bearish_count:      bearish signal 수
        total_signals:      입력된 전체 signal 수
        verdict:            판단 결과 ("buy_candidate" / "sell_candidate" / "hold")
    """

    total_score: int
    bullish_count: int
    bearish_count: int
    total_signals: int
    verdict: str


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def score_signals(signals: list[Signal]) -> ScoreResult:
    """Signal 리스트를 점수화하고 판단 결과를 반환한다.

    Args:
        signals: 점수화할 Signal 목록. 빈 리스트이면 score=0, verdict="hold" 반환.

    Returns:
        ScoreResult — 점수 및 판단 결과
    """
    total_score = 0
    bullish_count = 0
    bearish_count = 0

    for signal in signals:
        weight = _IMPORTANCE_WEIGHT[signal.importance]
        if signal.direction == Direction.BULLISH:
            total_score += weight
            bullish_count += 1
        elif signal.direction == Direction.BEARISH:
            total_score -= weight
            bearish_count += 1
        # NEUTRAL / MIXED → 0점, 카운트 제외

    if total_score >= _BUY_THRESHOLD:
        verdict = "buy_candidate"
    elif total_score <= _SELL_THRESHOLD:
        verdict = "sell_candidate"
    else:
        verdict = "hold"

    return ScoreResult(
        total_score=total_score,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        total_signals=len(signals),
        verdict=verdict,
    )
