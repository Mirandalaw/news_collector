"""Simulation report MVP.

SimulationResult를 받아 전체 성과와 종목별 결과를
사람이 읽기 쉬운 형태로 요약한다.

설계 원칙 (simulation-report.md 기준):
  - simulation 계산 로직과 출력 로직을 분리
  - 기존 SimulationResult 수정 없음
  - format_text()는 단순하고 가독성 높게 유지
  - 과도한 통계 지표 추가 금지
"""

from __future__ import annotations

from dataclasses import dataclass

from app.signals.simulation import PositionResult, SimulationResult

# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulationReport:
    """시뮬레이션 성과 요약 보고서.

    Attributes:
        total_trades: 전체 거래 수
        win_rate:     승률 (0.0 ~ 1.0)
        avg_pnl:      평균 손익률
        winners:      수익 포지션 수 (pnl > 0)
        losers:       손실 포지션 수 (pnl < 0)
        positions:    종목별 결과 (pnl 내림차순 정렬)
    """

    total_trades: int
    win_rate: float
    avg_pnl: float
    winners: int
    losers: int
    positions: list[PositionResult]

    def format_text(self) -> str:
        """사람이 읽을 수 있는 텍스트 요약을 반환한다."""
        if self.total_trades == 0:
            return "[시뮬레이션 결과]\n  거래 없음"

        lines: list[str] = [
            "[시뮬레이션 결과]",
            f"  총 거래:     {self.total_trades}건",
            f"  승률:        {self.win_rate:.0%}  ({self.winners}승 {self.losers}패)",
            f"  평균 손익:   {self.avg_pnl:+.2%}",
            "",
            "[종목별 결과]",
        ]

        for p in self.positions:
            pnl_str = f"{p.pnl:+.2%}"
            lines.append(
                f"  {p.symbol:8}  {pnl_str:8}  {p.exit_reason:12}  "
                f"{p.holding_days}일  "
                f"진입={p.entry_price:,.0f} → 청산={p.exit_price:,.0f}"
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def build_simulation_report(result: SimulationResult) -> SimulationReport:
    """SimulationResult에서 SimulationReport를 생성한다.

    Args:
        result: run_simulation()의 반환값

    Returns:
        SimulationReport — 정렬된 종목별 결과 및 요약 통계 포함
    """
    positions = _sort_positions(result.positions)

    winners = sum(1 for p in positions if p.pnl > 0)
    losers = sum(1 for p in positions if p.pnl < 0)

    return SimulationReport(
        total_trades=result.total_count,
        win_rate=result.win_rate,
        avg_pnl=result.avg_pnl,
        winners=winners,
        losers=losers,
        positions=positions,
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _sort_positions(positions: list[PositionResult]) -> list[PositionResult]:
    """pnl 내림차순, 동일 pnl 내 symbol 오름차순으로 정렬한다."""
    return sorted(positions, key=lambda p: (-p.pnl, p.symbol))
