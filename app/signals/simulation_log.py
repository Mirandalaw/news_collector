"""Simulation log MVP.

SimulationResult를 날짜별/종목별 CSV 레코드로 변환하고
파일로 누적 저장한다.

설계 원칙 (simulation-log.md 기준):
  - simulation 계산 로직과 저장 로직을 분리
  - 저장 실패가 전체 흐름을 중단하지 않음
  - CSV 기반 단순 구조 유지
  - 기존 simulation.py 수정 없음
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.signals.simulation import SimulationResult

logger = logging.getLogger(__name__)

# CSV 컬럼 순서
_FIELDNAMES = [
    "run_date",
    "total_trades",
    "win_rate",
    "avg_pnl",
    "symbol",
    "entry_price",
    "exit_price",
    "pnl",
    "exit_reason",
    "holding_days",
]


# ---------------------------------------------------------------------------
# 레코드 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulationLogRecord:
    """단일 포지션 로그 레코드 (CSV 1행에 대응).

    Attributes:
        run_date:     시뮬레이션 실행 날짜
        total_trades: 해당 실행의 전체 거래 수
        win_rate:     해당 실행의 승률
        avg_pnl:      해당 실행의 평균 손익률
        symbol:       종목 코드
        entry_price:  진입 가격
        exit_price:   청산 가격
        pnl:          손익률
        exit_reason:  청산 이유
        holding_days: 보유 일수
    """

    run_date: date
    total_trades: int
    win_rate: float
    avg_pnl: float
    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str
    holding_days: int

    def to_dict(self) -> dict:
        return {
            "run_date": self.run_date.isoformat(),
            "total_trades": self.total_trades,
            "win_rate": f"{self.win_rate:.4f}",
            "avg_pnl": f"{self.avg_pnl:.4f}",
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": f"{self.pnl:.4f}",
            "exit_reason": self.exit_reason,
            "holding_days": self.holding_days,
        }


# ---------------------------------------------------------------------------
# 변환 함수
# ---------------------------------------------------------------------------


def to_log_records(
    result: SimulationResult,
    run_date: date,
) -> list[SimulationLogRecord]:
    """SimulationResult를 SimulationLogRecord 리스트로 변환한다.

    포지션이 없으면 빈 리스트를 반환한다.

    Args:
        result:   run_simulation()의 반환값
        run_date: 시뮬레이션 실행 날짜

    Returns:
        list[SimulationLogRecord] — 포지션별 1개씩
    """
    return [
        SimulationLogRecord(
            run_date=run_date,
            total_trades=result.total_count,
            win_rate=result.win_rate,
            avg_pnl=result.avg_pnl,
            symbol=p.symbol,
            entry_price=p.entry_price,
            exit_price=p.exit_price,
            pnl=p.pnl,
            exit_reason=p.exit_reason,
            holding_days=p.holding_days,
        )
        for p in result.positions
    ]


# ---------------------------------------------------------------------------
# 저장 함수
# ---------------------------------------------------------------------------


def save_simulation_log(
    records: list[SimulationLogRecord],
    output_path: str | Path,
) -> bool:
    """SimulationLogRecord 목록을 CSV 파일에 저장한다.

    파일이 없으면 생성하고 헤더를 추가한다.
    파일이 이미 존재하면 기존 내용에 추가(append)한다.
    저장 실패 시 logger.warning 후 False를 반환한다.

    Args:
        records:     저장할 레코드 목록
        output_path: CSV 파일 경로

    Returns:
        True — 저장 성공 (레코드 없음 포함)
        False — 저장 실패
    """
    if not records:
        logger.debug("저장할 레코드 없음 | path=%s", output_path)
        return True

    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists()

        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
            if write_header:
                writer.writeheader()
            for record in records:
                writer.writerow(record.to_dict())

        logger.info("시뮬레이션 로그 저장 | path=%s | rows=%d", path, len(records))
        return True

    except Exception:
        logger.warning("시뮬레이션 로그 저장 실패 | path=%s", output_path, exc_info=True)
        return False
