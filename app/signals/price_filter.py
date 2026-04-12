"""Price filter MVP.

뉴스 기반 decision 결과를 가격/차트 조건으로 검증하는 순수 함수.

설계 원칙:
  - 가격 데이터 조회는 이 레이어의 책임이 아님 (호출자가 계산된 값을 전달)
  - 뉴스 판단(decision.py)과 가격 판단을 분리 유지
  - 자동 주문 실행 없음
  - RSI/MACD 등 기술지표 확장 금지
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_MAX_SURGE_RATIO = 0.15  # buy_candidate 급등 제외 상한
_MIN_SURGE_RATIO = -0.15  # sell_candidate 급락 반등 제외 하한


# ---------------------------------------------------------------------------
# 입력/출력 모델
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceFilterInput:
    """가격 필터에 필요한 가격/거래량 데이터.

    Attributes:
        close_price:  최근 종가
        ma20:         20일 이동평균
        volume:       최근 거래량
        avg_volume:   평균 거래량 (기준 기간)
        surge_ratio:  최근 N일 수익률 (급등/급락 감지용, 호출자 계산)
    """

    close_price: float
    ma20: float
    volume: float
    avg_volume: float
    surge_ratio: float


@dataclass(frozen=True)
class PriceFilterResult:
    """가격 필터 적용 결과.

    Attributes:
        symbol:             종목 코드
        news_decision:      뉴스 기반 판단 ("buy_candidate" / "sell_candidate" / "hold")
        price_filter_pass:  가격 조건 통과 여부
        final_candidate:    뉴스 판단이 buy/sell이고 가격 조건도 통과한 경우 True
        reason:             통과/탈락 이유 (사람이 읽는 텍스트)
    """

    symbol: str
    news_decision: str
    price_filter_pass: bool
    final_candidate: bool
    reason: str


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------


def apply_price_filter(
    symbol: str,
    news_decision: str,
    price_data: PriceFilterInput,
) -> PriceFilterResult:
    """뉴스 기반 판단 결과에 가격/차트 조건을 적용한다.

    Args:
        symbol:        종목 코드
        news_decision: make_decision()에서 반환된 종목별 판단 문자열
        price_data:    호출자가 계산하여 전달한 가격/거래량 데이터

    Returns:
        PriceFilterResult — 가격 조건 통과 여부 및 최종 후보 여부 포함
    """
    if news_decision == "buy_candidate":
        passed, reason = _check_buy(price_data)
    elif news_decision == "sell_candidate":
        passed, reason = _check_sell(price_data)
    else:
        passed = False
        reason = "hold: 가격 조건 검사 생략"

    return PriceFilterResult(
        symbol=symbol,
        news_decision=news_decision,
        price_filter_pass=passed,
        final_candidate=passed and news_decision in ("buy_candidate", "sell_candidate"),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _check_buy(p: PriceFilterInput) -> tuple[bool, str]:
    """buy_candidate 가격 조건을 검사한다.

    조건:
      1. 종가 > MA20
      2. 거래량 >= 평균 거래량
      3. surge_ratio <= 0.15 (급등 구간 제외)
    """
    if p.close_price <= p.ma20:
        return False, f"종가({p.close_price}) <= MA20({p.ma20}): 상승 추세 미확인"
    if p.volume < p.avg_volume * 0.7:
        return False, f"거래량({p.volume}) < 평균×0.7({p.avg_volume * 0.7:.0f}): 거래량 미확인"
    if p.surge_ratio > _MAX_SURGE_RATIO:
        return False, f"surge_ratio({p.surge_ratio:.2%}) > {_MAX_SURGE_RATIO:.0%}: 급등 구간 제외"
    return True, "buy 조건 통과: 종가>MA20, 거래량 확인, 급등 아님"


def _check_sell(p: PriceFilterInput) -> tuple[bool, str]:
    """sell_candidate 가격 조건을 검사한다.

    조건:
      1. 종가 < MA20
      2. surge_ratio >= -0.15 (급락 반등 구간 제외)
    """
    if p.close_price >= p.ma20:
        return False, f"종가({p.close_price}) >= MA20({p.ma20}): 하락 추세 미확인"
    if p.surge_ratio < _MIN_SURGE_RATIO:
        return False, (
            f"surge_ratio({p.surge_ratio:.2%}) < {_MIN_SURGE_RATIO:.0%}: 급락 반등 구간 제외"
        )
    return True, "sell 조건 통과: 종가<MA20, 급락 반등 아님"
