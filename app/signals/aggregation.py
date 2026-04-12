"""Signal aggregation MVP.

시장 단위 및 종목 단위로 signal을 집계하고
score_signals를 재사용하여 점수를 계산한다.

설계 원칙:
  - 집계 로직(분리)과 점수 계산(score_signals)을 분리
  - 초기 버전은 단순 dictionary 기반
  - 자동매매 실행 로직 없음
  - 차트/가격 필터와의 결합은 다음 단계
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.signals.models import Signal
from app.signals.scoring import ScoreResult, score_signals

# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AggregationResult:
    """시장 및 종목 단위 집계 결과.

    Attributes:
        market_score:  시장 전체 signal 점수 (symbols가 빈 signal 기준)
        by_symbol:     종목별 점수. key = 종목 코드, value = ScoreResult
    """

    market_score: ScoreResult
    by_symbol: dict[str, ScoreResult]


# ---------------------------------------------------------------------------
# 집계 함수
# ---------------------------------------------------------------------------


def aggregate_signals(signals: list[Signal]) -> AggregationResult:
    """Signal 리스트를 시장/종목 단위로 집계하고 점수를 반환한다.

    시장 signal: signal.symbols가 빈 리스트인 signal
    종목 signal: signal.symbols에 종목 코드가 있는 signal (한 signal이 여러 종목에 속할 수 있음)

    Args:
        signals: SignalEngine.analyze()로 생성된 Signal 목록

    Returns:
        AggregationResult — market_score와 by_symbol 포함
    """
    market_signals = _collect_market_signals(signals)
    symbol_map = _collect_symbol_signals(signals)

    return AggregationResult(
        market_score=score_signals(market_signals),
        by_symbol={sym: score_signals(sigs) for sym, sigs in symbol_map.items()},
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _collect_market_signals(signals: list[Signal]) -> list[Signal]:
    """symbols가 없는(시장 전체) signal만 반환한다."""
    return [s for s in signals if not s.symbols]


def _collect_symbol_signals(signals: list[Signal]) -> dict[str, list[Signal]]:
    """종목 코드별로 signal을 묶어 반환한다.

    한 signal이 여러 종목 코드를 가지면 각 종목에 모두 포함된다.
    """
    result: dict[str, list[Signal]] = defaultdict(list)
    for signal in signals:
        for sym in signal.symbols:
            result[sym].append(signal)
    return dict(result)
