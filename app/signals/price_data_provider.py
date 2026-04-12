"""Price data provider MVP.

종목 코드 목록을 입력받아 FinanceDataReader로 시세 데이터를 조회하고
PriceFilterInput 딕셔너리를 생성한다.

설계 원칙:
  - 조회 + 지표 계산 + PriceFilterInput 생성만 담당
  - signal/decision/price filter 적용은 이 레이어의 책임이 아님
  - 종목별 조회 실패는 skip (브리핑 전체를 실패시키지 않음)
  - 자동 주문 실행 없음
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import FinanceDataReader as fdr
import pandas as pd

from app.signals.price_filter import PriceFilterInput

logger = logging.getLogger(__name__)

# ma20 계산에 필요한 최소 데이터 행 수
_MIN_ROWS = 20


def fetch_price_inputs(
    symbols: list[str],
    lookback_days: int = 40,
    surge_window: int = 5,
) -> dict[str, PriceFilterInput]:
    """종목 코드 목록에 대해 PriceFilterInput을 조회·계산하여 반환한다.

    데이터 조회 실패 또는 데이터 부족 종목은 결과에서 제외된다.
    apply_price_filters의 price_inputs 인자로 직접 전달 가능하다.

    Args:
        symbols:      종목 코드 목록 (KRX 6자리 코드, 예: ["005930", "035420"])
        lookback_days: 시세 조회 기간 (달력일 기준). ma20 확보를 위해 40일 이상 권장.
        surge_window:  surge_ratio 계산 기준 기간 (거래일 수)

    Returns:
        dict[str, PriceFilterInput] — 조회 성공 종목만 포함
    """
    if not symbols:
        return {}

    start = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    results: dict[str, PriceFilterInput] = {}

    for symbol in symbols:
        try:
            df = fdr.DataReader(symbol, start)
            price_input = _build_price_input(df, surge_window)
            if price_input is None:
                logger.warning("시세 데이터 부족 | symbol=%s | rows=%d", symbol, len(df))
                continue
            results[symbol] = price_input
        except Exception:
            logger.warning("시세 조회 실패 | symbol=%s", symbol, exc_info=True)

    logger.info("시세 조회 완료 | 요청=%d건 / 성공=%d건", len(symbols), len(results))
    return results


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _build_price_input(df: pd.DataFrame, surge_window: int) -> PriceFilterInput | None:
    """DataFrame에서 PriceFilterInput을 계산한다.

    데이터가 부족하면 None을 반환한다.
    """
    needed = max(_MIN_ROWS, surge_window + 1)
    if len(df) < needed:
        return None

    close = df["Close"]
    volume = df["Volume"]

    close_price = float(close.iloc[-1])
    ma20 = float(close.iloc[-_MIN_ROWS:].mean())
    vol = float(volume.iloc[-1])
    avg_volume = float(volume.iloc[-_MIN_ROWS:].mean())

    prev_close = float(close.iloc[-(surge_window + 1)])
    surge_ratio = (close_price - prev_close) / prev_close if prev_close != 0 else 0.0

    return PriceFilterInput(
        close_price=close_price,
        ma20=ma20,
        volume=vol,
        avg_volume=avg_volume,
        surge_ratio=surge_ratio,
    )
