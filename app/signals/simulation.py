"""Trade candidate simulation MVP.

TradeCandidateReport를 입력받아 가상 포지션을 생성하고
손절/익절/타임아웃 조건으로 PnL을 계산한다.

설계 원칙 (simulation.md 기준):
  - 실제 주문 없음 — 가상 진입만 수행
  - 단순 규칙 기반: 손절 -3%, 익절 +5%, 최대 보유 5일
  - 복잡한 전략 금지
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.signals.trade_candidate_output import TradeCandidateReport

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_STOP_LOSS = -0.03  # -3%
_TAKE_PROFIT = 0.05  # +5%
_MAX_HOLDING_DAYS = 5

_EXIT_STOP_LOSS = "stop_loss"
_EXIT_TAKE_PROFIT = "take_profit"
_EXIT_TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DayBar:
    """하루 OHLCV 데이터.

    Attributes:
        date:   거래일
        open:   시가
        high:   고가
        low:    저가
        close:  종가
        volume: 거래량
    """

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class PositionResult:
    """단일 가상 포지션 결과.

    Attributes:
        symbol:       종목 코드
        news_decision: 뉴스 기반 판단
        entry_price:  진입 가격 (진입일 종가)
        exit_price:   청산 가격
        pnl:          손익률 (소수, 예: 0.05 = +5%)
        exit_reason:  청산 이유 ("stop_loss" / "take_profit" / "timeout")
        holding_days: 보유 일수
    """

    symbol: str
    news_decision: str
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str
    holding_days: int


@dataclass(frozen=True)
class SimulationResult:
    """전체 시뮬레이션 결과.

    Attributes:
        positions: 포지션 결과 목록 (후보 순서 유지)
    """

    positions: list[PositionResult]

    @property
    def total_count(self) -> int:
        return len(self.positions)

    @property
    def win_count(self) -> int:
        return sum(1 for p in self.positions if p.pnl > 0)

    @property
    def win_rate(self) -> float:
        if not self.positions:
            return 0.0
        return self.win_count / self.total_count

    @property
    def avg_pnl(self) -> float:
        if not self.positions:
            return 0.0
        return sum(p.pnl for p in self.positions) / self.total_count


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def run_simulation(
    report: TradeCandidateReport,
    price_history: dict[str, list[DayBar]],
) -> SimulationResult:
    """TradeCandidateReport의 final_candidate 종목에 시뮬레이션을 실행한다.

    price_history에 해당 종목 데이터가 없거나 부족하면 해당 종목을 건너뛴다.

    Args:
        report:        build_trade_candidate_report()의 반환값
        price_history: 종목별 일별 DayBar 목록.
                       bars[0]이 진입일, bars[1:]가 이후 거래일.
                       최소 2개 이상 bars 필요 (진입일 + 최소 1일).

    Returns:
        SimulationResult — 포지션별 PnL 및 요약 통계
    """
    positions: list[PositionResult] = []

    for candidate in report.candidates:
        bars = price_history.get(candidate.symbol)
        if not bars or len(bars) < 2:
            continue

        result = _simulate_position(candidate.symbol, candidate.news_decision, bars)
        if result is not None:
            positions.append(result)

    return SimulationResult(positions=positions)


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _simulate_position(
    symbol: str,
    news_decision: str,
    bars: list[DayBar],
) -> PositionResult | None:
    """단일 종목 가상 포지션을 시뮬레이션한다.

    진입: bars[0].close
    이후 bars[1:]를 순서대로 확인하여 손절/익절/타임아웃 조건 적용.
    """
    entry_price = bars[0].close
    if entry_price <= 0:
        return None

    stop_price = entry_price * (1 + _STOP_LOSS)
    target_price = entry_price * (1 + _TAKE_PROFIT)

    for day_idx, bar in enumerate(bars[1 : _MAX_HOLDING_DAYS + 1], start=1):
        # 손절 확인: 저가가 손절가 이하
        if bar.low <= stop_price:
            exit_price = stop_price
            return PositionResult(
                symbol=symbol,
                news_decision=news_decision,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=_calc_pnl(entry_price, exit_price),
                exit_reason=_EXIT_STOP_LOSS,
                holding_days=day_idx,
            )

        # 익절 확인: 고가가 익절가 이상
        if bar.high >= target_price:
            exit_price = target_price
            return PositionResult(
                symbol=symbol,
                news_decision=news_decision,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=_calc_pnl(entry_price, exit_price),
                exit_reason=_EXIT_TAKE_PROFIT,
                holding_days=day_idx,
            )

    # 타임아웃: 최대 보유 기간 이후 종가 청산
    last_bar = bars[min(_MAX_HOLDING_DAYS, len(bars) - 1)]
    return PositionResult(
        symbol=symbol,
        news_decision=news_decision,
        entry_price=entry_price,
        exit_price=last_bar.close,
        pnl=_calc_pnl(entry_price, last_bar.close),
        exit_reason=_EXIT_TIMEOUT,
        holding_days=min(_MAX_HOLDING_DAYS, len(bars) - 1),
    )


def _calc_pnl(entry: float, exit_: float) -> float:
    """손익률을 계산한다. (exit - entry) / entry"""
    return (exit_ - entry) / entry
