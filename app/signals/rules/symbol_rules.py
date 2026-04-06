"""종목/기업 레벨 시그널 규칙.

적용 대상: article_type = 'company' | 'event' 또는 종목 태그가 붙은 기사
규칙 우선순위: earnings_surprise > regulatory > analyst > capex/contract

【단타 규칙】 실적 서프라이즈/쇼크, 단기 촉매 이벤트
【장기 규칙】 규제 리스크, 전략적 투자, 비즈니스 모델 변화
"""

from app.signals.models import Direction, Horizon, Importance
from app.signals.rules.base import KeywordSignalRule

# ---------------------------------------------------------------------------
# ★★★ HIGH — 단기 (실적 서프라이즈/쇼크)
# ---------------------------------------------------------------------------

EARNINGS_BEAT = KeywordSignalRule(
    name="earnings_beat",
    trigger_keywords=(
        "earnings beat",
        "어닝 서프라이즈",
        "실적 서프라이즈",
        "revenue beat",
        "매출 상회",
        "영업이익 급증",
        "순이익 상회",
        "beat expectations",
        "beat consensus",
        "exceed estimate",
        "분기 서프라이즈",
    ),
    veto_keywords=("earnings miss", "어닝 쇼크", "실적 부진"),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason=("실적 서프라이즈 → 즉각적인 주가 리레이팅 기대. 다음 분기 가이던스도 함께 확인 필요."),
    action_hint=(
        "실적 발표 후 갭업 시 추격 매수보다 눌림목 대기 전략 검토. 가이던스 하향 리스크 주의."
    ),
    target_types=("company", "event"),
)

EARNINGS_MISS = KeywordSignalRule(
    name="earnings_miss",
    trigger_keywords=(
        "earnings miss",
        "어닝 쇼크",
        "실적 쇼크",
        "실적 부진",
        "revenue miss",
        "매출 하회",
        "영업이익 급감",
        "순이익 감소",
        "missed expectations",
        "missed consensus",
        "below estimate",
    ),
    veto_keywords=("earnings beat", "어닝 서프라이즈", "실적 서프라이즈"),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="실적 쇼크 → 주가 급락 가능성. 가이던스 하향 동반 여부에 따라 낙폭 결정.",
    action_hint="손절 기준 사전 설정 확인. 단기 반등 시 비중 축소 검토. 업황 전반 점검 필요.",
    target_types=("company", "event"),
)

GUIDANCE_RAISE = KeywordSignalRule(
    name="guidance_raise",
    trigger_keywords=(
        "raised guidance",
        "guidance raised",
        "가이던스 상향",
        "full-year raised",
        "outlook raised",
        "전망 상향",
        "upward revision",
        "목표 상향",
    ),
    veto_keywords=("guidance cut", "guidance lowered", "가이던스 하향"),
    direction=Direction.BULLISH,
    horizon=Horizon.BOTH,
    importance=Importance.HIGH,
    reason="가이던스 상향 → 경영진의 향후 실적 자신감. 장기 투자자에게 긍정적 신호.",
    action_hint="단기 매수 촉매로 작동 가능. 장기 포지션 유지 근거 강화.",
    target_types=("company",),
)

GUIDANCE_CUT = KeywordSignalRule(
    name="guidance_cut",
    trigger_keywords=(
        "guidance cut",
        "guidance lowered",
        "가이던스 하향",
        "outlook cut",
        "전망 하향",
        "downward revision",
        "경고 발표",
        "profit warning",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.BOTH,
    importance=Importance.HIGH,
    reason="가이던스 하향 → 업황 악화 또는 구조적 문제 신호. 실적 하강 사이클 진입 가능성.",
    action_hint="비중 축소 검토. 경쟁사 동반 하향 여부 확인 후 섹터 전체 리스크 점검.",
    target_types=("company",),
)

# ---------------------------------------------------------------------------
# ★★★ HIGH — 장기 (규제, 소송)
# ---------------------------------------------------------------------------

REGULATORY_RISK = KeywordSignalRule(
    name="regulatory_risk",
    trigger_keywords=(
        "규제",
        "제재",
        "벌금",
        "fine",
        "antitrust",
        "공정위",
        "ftc",
        "소송 제기",
        "lawsuit filed",
        "investigation launched",
        "조사 착수",
        "ban imposed",
        "수출 금지",
        "export ban",
        "sanctions imposed",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.LONG,
    importance=Importance.HIGH,
    reason="규제·법적 리스크 → 중장기 비용 증가 및 비즈니스 모델 제약 가능성",
    action_hint="규제 결론까지 불확실성 지속. 비중 축소 또는 헤지 고려. 유사 규제 선례 참고.",
    target_types=("company",),
)

CAPEX_EXPANSION = KeywordSignalRule(
    name="capex_expansion",
    trigger_keywords=(
        "투자 확대",
        "공장 증설",
        "fab expansion",
        "capex increase",
        "대규모 투자",
        "신규 공장",
        "생산 능력 확대",
        "capacity expansion",
        "billion investment",
        "조 원 투자",
        "설비 투자",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.MEDIUM,
    reason="대규모 CAPEX 발표 → 장기 성장에 대한 경영진 확신. 단기 FCF 감소 주의.",
    action_hint="단기 주가 영향 제한적. 장기 투자자에게 긍정적. 단기 FCF 압박 여부 확인.",
    target_types=("company",),
)

# ---------------------------------------------------------------------------
# ★★☆ MEDIUM — 단기 (애널리스트, 계약, M&A)
# ---------------------------------------------------------------------------

ANALYST_UPGRADE = KeywordSignalRule(
    name="analyst_upgrade",
    trigger_keywords=(
        "buy rating",
        "매수 등급",
        "outperform",
        "overweight",
        "upgraded to buy",
        "목표가 상향",
        "price target raised",
        "top pick",
        "강력 매수",
    ),
    veto_keywords=("downgrade", "sell rating", "underperform", "목표가 하향"),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="애널리스트 상향 조정 → 단기 수급 개선 가능성. 단, 수수료 동기 고려 필요.",
    action_hint="단독 지표로 매수 결정 지양. 실적·밸류에이션 근거 직접 확인 권장.",
    target_types=("company",),
)

ANALYST_DOWNGRADE = KeywordSignalRule(
    name="analyst_downgrade",
    trigger_keywords=(
        "sell rating",
        "매도 등급",
        "underperform",
        "underweight",
        "downgraded to sell",
        "목표가 하향",
        "price target cut",
        "neutral from buy",
        "avoid",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="애널리스트 하향 → 기관 수급 감소 가능성. 근거 리포트 확인 필요.",
    action_hint="하향 근거(밸류에이션·실적·경쟁) 직접 확인. 단기 매도 촉매 가능성 참고.",
    target_types=("company",),
)

MA_DEAL = KeywordSignalRule(
    name="ma_deal",
    trigger_keywords=(
        "acquisition",
        "merger",
        "인수",
        "합병",
        "m&a",
        "takeover bid",
        "인수 발표",
        "전략적 인수",
        "strategic acquisition",
        "buyout",
    ),
    direction=Direction.MIXED,
    horizon=Horizon.BOTH,
    importance=Importance.MEDIUM,
    reason="M&A 발표 → 피인수 기업 주가 프리미엄 기대, 인수 기업은 단기 하락 경우 많음",
    action_hint="피인수 기업: 단기 매수 기회 가능. 인수 기업: 딜 프리미엄·통합 비용 분석 필요.",
    target_types=("company",),
)

CONTRACT_WIN = KeywordSignalRule(
    name="contract_win",
    trigger_keywords=(
        "수주",
        "계약 체결",
        "contract won",
        "deal signed",
        "계약 성사",
        "major contract",
        "대형 수주",
        "공급 계약",
        "supply agreement",
    ),
    veto_keywords=("계약 해지", "contract terminated", "deal cancelled"),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="신규 수주/계약 → 단기 매출 가시성 향상. 규모에 따라 주가 반응 차이.",
    action_hint="계약 규모와 마진율 확인. 일회성인지 반복성 계약인지 구분 중요.",
    target_types=("company",),
)

DIVIDEND_INCREASE = KeywordSignalRule(
    name="dividend_increase",
    trigger_keywords=(
        "배당 증가",
        "dividend increase",
        "dividend raised",
        "special dividend",
        "자사주 매입",
        "buyback announced",
        "주주환원 강화",
        "shareholder return",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.MEDIUM,
    reason="배당 증가/자사주 매입 → 잉여현금흐름 자신감, 주주 친화 정책 강화",
    action_hint="장기 배당 투자자에게 긍정적. 단, FCF 대비 과도한 환원인지 확인.",
    target_types=("company",),
)

PARTNERSHIP_STRATEGIC = KeywordSignalRule(
    name="partnership_strategic",
    trigger_keywords=(
        "strategic partnership",
        "전략적 파트너십",
        "joint venture",
        "합작법인",
        "업무협약",
        "mou 체결",
        "협력 발표",
        "ai partnership",
        "ai 협력",
        "공동 개발",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.LOW,
    reason="전략적 파트너십 → 장기 성장 옵션 확보. 단, MOU 수준은 실질 효과 불확실.",
    action_hint="구속력 있는 계약인지 MOU인지 구분. 파트너의 시너지 실현 가능성 검토.",
    target_types=("company",),
)
