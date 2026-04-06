"""거시경제 / 시장 전체 시그널 규칙.

적용 대상: article_type = 'market' 또는 키워드가 명확한 market 기사
규칙 우선순위 (중요도 순): HIGH > MEDIUM > LOW
시간 축: SHORT(단기 1~5일) vs LONG(장기 수주~수개월)

【단타 규칙】 Fed, CPI, 지수 급변, VIX
【장기 규칙】 금리 사이클 전환, 구조적 인플레이션, 경기침체

각 규칙은 독립적으로 발동 가능 (한 기사에 여러 규칙이 동시 발동 가능).
"""

from app.signals.models import Direction, Horizon, Importance
from app.signals.rules.base import KeywordSignalRule

# ---------------------------------------------------------------------------
# ★★★ HIGH — 단기 (Fed, 실적 이벤트, 시장 충격)
# ---------------------------------------------------------------------------

FED_RATE_CUT = KeywordSignalRule(
    name="fed_rate_cut",
    trigger_keywords=(
        "rate cut",
        "금리 인하",
        "금리인하",
        "rate cut expected",
        "dovish",
        "완화적",
        "pivot",
        "피벗",
    ),
    veto_keywords=("rate hike", "금리 인상", "hawkish"),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="연준 또는 한국은행의 금리 인하 시사 → 유동성 확대 기대, 주식 밸류에이션 상승 압력",
    action_hint="단기 성장주·리츠 비중 확대 검토. 단, 실제 인하 발표 전까지 불확실성 유지.",
    target_types=("market",),
)

FED_RATE_HIKE = KeywordSignalRule(
    name="fed_rate_hike",
    trigger_keywords=(
        "rate hike",
        "금리 인상",
        "금리인상",
        "rate increase",
        "hawkish",
        "긴축",
        "tightening",
    ),
    veto_keywords=("rate cut", "금리 인하", "pause", "hold"),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="금리 인상 기조 확인 → 할인율 상승, 고평가 성장주 밸류에이션 압박",
    action_hint="단기 기술주 비중 축소 검토. 금융주·단기채 상대 강세 가능성 참고.",
    target_types=("market",),
)

FED_HOLD_UNCERTAIN = KeywordSignalRule(
    name="fed_hold_uncertain",
    trigger_keywords=(
        "rate hold",
        "금리 동결",
        "금리동결",
        "pause",
        "데이터 의존",
        "data-dependent",
        "wait and see",
    ),
    direction=Direction.NEUTRAL,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="Fed 동결 또는 방향성 불확실 → 단기 시장은 관망 모드 진입 가능",
    action_hint="방향성 확인 전까지 레버리지 포지션 자제. 변동성 확대 구간 주의.",
    target_types=("market",),
)

INFLATION_HOT = KeywordSignalRule(
    name="inflation_hot",
    trigger_keywords=(
        "cpi beat",
        "cpi 상회",
        "inflation surged",
        "인플레이션 상승",
        "물가 상승",
        "pce beat",
        "hot inflation",
        "기대 이상 물가",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.BOTH,
    importance=Importance.HIGH,
    reason="인플레이션 예상치 상회 → 금리 인하 기대 후퇴, 채권 금리 상승 압박",
    action_hint="인플레이션 헤지 자산(원자재·에너지주) 비중 고려. 장기채 보유 비중 재점검.",
    target_types=("market",),
)

INFLATION_COOL = KeywordSignalRule(
    name="inflation_cool",
    trigger_keywords=(
        "cpi fell",
        "cpi 하락",
        "cpi miss",
        "inflation eased",
        "인플레이션 둔화",
        "물가 안정",
        "deflation",
        "디스인플레이션",
        "cooling inflation",
        "below expectations",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="물가 둔화 확인 → 금리 인하 기대 강화, 성장주 반등 가능성",
    action_hint="기술주·소비재 단기 매수 기회 탐색. 채권도 단기 강세 가능.",
    target_types=("market",),
)

# ---------------------------------------------------------------------------
# ★★★ HIGH — 장기 (경기침체, 구조적 전환)
# ---------------------------------------------------------------------------

RECESSION_RISK = KeywordSignalRule(
    name="recession_risk",
    trigger_keywords=(
        "recession",
        "경기침체",
        "gdp contraction",
        "gdp 감소",
        "경기 위축",
        "soft landing failed",
        "hard landing",
        "inverted yield curve",
        "장단기 금리 역전",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.LONG,
    importance=Importance.HIGH,
    reason="경기침체 신호 → 기업 실적 전반 하강 사이클 진입 가능성",
    action_hint="경기방어주(헬스케어·유틸리티·필수소비재) 비중 강화 검토. 현금 비중 확대.",
    target_types=("market",),
)

RATE_CYCLE_PIVOT = KeywordSignalRule(
    name="rate_cycle_pivot",
    trigger_keywords=(
        "rate cycle",
        "통화정책 전환",
        "easing cycle",
        "피벗 확인",
        "first rate cut",
        "첫 금리 인하",
        "rate cut cycle",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.HIGH,
    reason="금리 인하 사이클 시작 → 장기적 유동성 확대, 성장주·부동산·리츠 리레이팅",
    action_hint="장기 성장주·리츠 비중 점진적 확대 검토. 단, 경기 연착륙 여부 병행 확인.",
    target_types=("market",),
)

# ---------------------------------------------------------------------------
# ★★☆ MEDIUM — 단기 (원자재, 달러, 지수)
# ---------------------------------------------------------------------------

OIL_SURGE = KeywordSignalRule(
    name="oil_surge",
    trigger_keywords=(
        "oil surge",
        "유가 급등",
        "oil price spike",
        "wti 상승",
        "brent 상승",
        "oil supply cut",
        "opec cuts",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="유가 급등 → 수입국(한국) 비용 상승, 항공·운송·제조업 마진 압박",
    action_hint="에너지 비용 민감 섹터(항공·운송·화학) 노출 점검. 정유주는 단기 강세 가능.",
)

OIL_DROP = KeywordSignalRule(
    name="oil_drop",
    trigger_keywords=(
        "oil price fell",
        "유가 하락",
        "oil drop",
        "wti 하락",
        "brent 하락",
        "oil demand weak",
    ),
    direction=Direction.MIXED,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="유가 하락 → 수입국 비용 완화(긍정), 경기 둔화 신호일 수 있음(부정)",
    action_hint="수혜·피해 섹터 분리 확인. 단순 에너지 비용 하락인지 수요 위축 신호인지 구분 필요.",
)

DOLLAR_STRONG = KeywordSignalRule(
    name="dollar_strong",
    trigger_keywords=(
        "dollar index up",
        "달러 강세",
        "원달러 상승",
        "usd strengthens",
        "strong dollar",
        "달러 인덱스 상승",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="달러 강세 → 신흥국 자금 유출 압력, 원화 약세로 수입 물가 상승",
    action_hint="원화 표시 자산 비중 점검. 달러 자산·수출주 상대 강세 가능.",
)

MARKET_RALLY = KeywordSignalRule(
    name="market_rally",
    trigger_keywords=(
        "코스피 상승",
        "코스닥 상승",
        "s&p 500 rallied",
        "nasdaq surged",
        "증시 상승",
        "주가 급등",
        "market rally",
        "bullish momentum",
    ),
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="지수 급등 → 단기 모멘텀 상승. 단, 과매수 여부 확인 필요.",
    action_hint="모멘텀 추종 매매 주의. 상승 이유(실적·정책·수급) 파악 후 판단.",
)

MARKET_CRASH = KeywordSignalRule(
    name="market_crash",
    trigger_keywords=(
        "폭락",
        "급락",
        "crash",
        "market selloff",
        "코스피 급락",
        "black monday",
        "circuit breaker",
        "서킷브레이커",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="시장 급락 → 패닉셀링 또는 구조적 매도 압력. 단기 변동성 극대화 국면.",
    action_hint="추격 매도 자제. 원인(유동성/실적/지정학) 파악 후 대응. VIX 수준 확인.",
)

VIX_SPIKE = KeywordSignalRule(
    name="vix_spike",
    trigger_keywords=(
        "vix surged",
        "vix spiked",
        "vix 급등",
        "공포지수 상승",
        "fear index",
        "volatility spike",
    ),
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="VIX(공포지수) 급등 → 시장 불확실성 극대화, 단기 매도 압력 확대",
    action_hint="단기 포지션 축소 또는 헤지 검토. VIX 30 이상 시 역발상 매수 기회 탐색.",
)
