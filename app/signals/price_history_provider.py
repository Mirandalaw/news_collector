"""Simulation price history provider.

종목 코드 목록을 받아 FinanceDataReader로 일봉 OHLCV를 조회하고
DayBar 리스트를 반환한다.

설계 원칙 (simulation-history-provider.md 기준):
  - 순수 데이터 공급만 수행
  - 시뮬레이션/가격 계산 로직 없음
  - 조회 실패 종목은 skip (예외 전파 금지)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import FinanceDataReader as fdr

from app.signals.simulation import DayBar

logger = logging.getLogger(__name__)

# 시뮬레이션에 유효한 최소 DayBar 수 (진입일 + 1일 이상)
_MIN_BARS = 2


def fetch_price_history(
    symbols: list[str],
    lookback_days: int = 30,
) -> dict[str, list[DayBar]]:
    """종목별 일봉 OHLCV를 조회하여 DayBar 리스트를 반환한다.

    데이터 부족 또는 조회 실패 종목은 결과에서 제외된다.

    Args:
        symbols:      종목 코드 목록 (KRX 6자리 또는 해외 티커)
        lookback_days: 조회 기간 (달력일 기준)

    Returns:
        dict[str, list[DayBar]] — 조회 성공 종목만 포함.
        DayBar 리스트는 날짜 오름차순 (oldest → newest).
    """
    if not symbols:
        return {}

    start = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    results: dict[str, list[DayBar]] = {}

    for symbol in symbols:
        try:
            df = fdr.DataReader(symbol, start)
            if df is None or len(df) < _MIN_BARS:
                rows = len(df) if df is not None else 0
                logger.warning("데이터 부족 | symbol=%s | rows=%d", symbol, rows)
                continue
            results[symbol] = _to_day_bars(df)
        except Exception:
            logger.warning("조회 실패 | symbol=%s", symbol, exc_info=True)

    logger.info("히스토리 조회 완료 | 요청=%d건 / 성공=%d건", len(symbols), len(results))
    return results


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _to_day_bars(df) -> list[DayBar]:
    """FinanceDataReader DataFrame을 DayBar 리스트로 변환한다."""
    bars: list[DayBar] = []
    for ts, row in df.iterrows():
        bars.append(
            DayBar(
                date=ts.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return bars
