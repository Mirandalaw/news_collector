"""이벤트 기반 시그널 규칙.

기존 keyword 규칙이 충분히 커버하지 못하는 영역을 보완한다.

적용 대상:
  - geopolitics: article_type 무관, 지정학 키워드 포함 기사
  - earnings: article_type 무관 (symbol_rules의 company/event 한정 규칙 보완)

현재 포함하지 않는 영역:
  - rate: FED_RATE_CUT/HIKE로 충분히 커버됨
  - oil: OIL_SURGE/OIL_DROP으로 커버됨
  - policy: 방향 오탐 위험으로 이번 단계 제외
"""

from app.signals.models import Direction, Horizon, Importance
from app.signals.rules.base import KeywordSignalRule

# ---------------------------------------------------------------------------
# 지정학 (geopolitics)
# ---------------------------------------------------------------------------

GEOPOLITICS_BEARISH = KeywordSignalRule(
    name="geopolitics_bearish",
    trigger_keywords=(
        "지정학",
        "북한",
        "중동",
        "이스라엘",
        "러시아",
        "우크라이나",
        "대만 해협",
        "하마스",
        "나토",
        "nato",
        "전쟁 위기",
        "군사 충돌",
        "봉쇄",
        "제재 강화",
    ),
    # 지정학 이벤트는 "우려" 같은 부정어가 동반되어도 bearish 유지
    negation_keywords=(),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="지정학적 리스크 → 안전자산 선호, 위험자산 회피 심리 확대",
    action_hint="에너지·방산 섹터 단기 수혜 가능. 수출 의존도 높은 종목 노출 점검.",
)

# ---------------------------------------------------------------------------
# 실적 (earnings) — symbol_rules 보완 (article_type 제한 없음, MEDIUM)
# ---------------------------------------------------------------------------

EVENT_EARNINGS_BEAT = KeywordSignalRule(
    name="event_earnings_beat",
    trigger_keywords=(
        "어닝 서프라이즈",
        "실적 서프라이즈",
        "영업이익 급증",
        "깜짝 실적",
        "어닝 비트",
        "예상 상회",
        "컨센서스 상회",
        "시장 예상 웃돌",
        "실적 호조",
        "분기 최대",
    ),
    veto_keywords=("어닝 쇼크", "실적 쇼크", "실적 부진", "예상 하회"),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="실적 서프라이즈 → 단기 주가 리레이팅 기대",
    action_hint="갭업 시 추격보다 눌림목 대기. 가이던스 방향도 함께 확인.",
)

EVENT_EARNINGS_MISS = KeywordSignalRule(
    name="event_earnings_miss",
    trigger_keywords=(
        "어닝 쇼크",
        "실적 쇼크",
        "실적 부진",
        "영업이익 급감",
        "예상 하회",
        "컨센서스 하회",
        "시장 예상 밑돌",
        "실적 충격",
        "분기 적자",
        "영업손실",
    ),
    veto_keywords=("어닝 서프라이즈", "실적 서프라이즈", "예상 상회"),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="실적 쇼크 → 단기 주가 하락 압력",
    action_hint="손절 기준 사전 확인. 단기 반등 시 비중 축소 검토.",
)
