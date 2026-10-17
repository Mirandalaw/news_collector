"""농산물 수급 사건 규칙 (해커톤 기획서 4장의 13개 이벤트 유형 + 정부 수매).

기존 KeywordSignalRule 을 그대로 쓴다. 의미 매핑:
  Direction.BULLISH = 공급 감소 → 가격 상승 요인 (+1)
  Direction.BEARISH = 공급 증가·수요 감소 → 가격 하락 요인 (−1)
  Horizon.SHORT     = 즉시~단기 (10일 일별 예측 보정)
  Horizon.LONG      = 중기 (2순·3순 후 예측 보정)
  Horizon.BOTH      = 둘 다
  Importance        = 과거 방향 적중률 추정치. HIGH=공시성(비축·TRQ·특보), MEDIUM=산지 동향,
                      LOW=심리·전망 기사 (발동 가중 0.5)

규칙은 품목 태깅(agri_watchlist)과 독립이다. target_symbols 를 비워 두면 기사에 붙은
품목 전부에 적용되고, 수입·저장 사건처럼 품목이 정해진 규칙만 target_symbols 로 제한한다.

negation_keywords 는 기본값(우려·둔화 등)이 주식 문맥용이라 농산물 규칙에서는 모두 비운다.
사후 보도("배추 한 포기 2만원 급등")는 POSTHOC_VETO 로 전 규칙에서 공통 제외한다.
"""

from app.signals.models import Direction, Horizon, Importance
from app.signals.rules.base import KeywordSignalRule

# 기사 성격상 수급 사건이 아닌 문맥 — 모든 농산물 규칙에서 발동 취소
# (사후 보도 표현 "폭등·치솟·금배추"는 더 이상 veto 하지 않는다: 2021~2024 소급 코퍼스에서 정부 대책
#  기사의 대부분이 제목에 그런 표현을 함께 쓰고 있어 사건을 통째로 놓쳤다. 사후 보도 여부는
#  agri_features.is_posthoc() 가 별도 플래그로 낸다.)
POSTHOC_VETO: tuple[str, ...] = (
    "레시피",
    "맛집",
    "사설",
    "칼럼",
    "원산지 단속",
    "원산지 표시",
)

# 사후 보도 표현 — 규칙 발동은 막지 않고, 사건이 하나도 없을 때 "가격 반영 완료" 플래그로만 쓴다
POSTHOC_MARKERS: tuple[str, ...] = (
    "금배추",
    "금값",
    "한 포기에",
    "포기당 ",
    "껑충",
    "치솟",
    "폭등",
    "폭락",
    "급등",
    "급락",
)

_NO_NEG: tuple[str, ...] = ()

# ---------------------------------------------------------------------------
# A. 공급 감소 (가격 상승 요인)
# ---------------------------------------------------------------------------

AGRI_TYPHOON = KeywordSignalRule(
    name="agri_typhoon",
    trigger_keywords=("태풍", "강풍 피해", "침수 피해", "농작물 피해"),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.BOTH,
    importance=Importance.HIGH,
    reason="태풍·침수 → 산지 출하 차질, 단기 공급 감소",
    action_hint="피해 면적(ha)·지역이 기사에 있으면 magnitude로 추출",
)

AGRI_HEAVY_RAIN = KeywordSignalRule(
    name="agri_heavy_rain",
    trigger_keywords=("폭우", "집중호우", "호우 피해", "장마 피해", "물에 잠"),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="폭우 → 수확·출하 지연, 단기 공급 감소",
    action_hint="주산지(해남·평창·무안·의성·영양 등) 언급 여부 확인",
)

AGRI_HEAT = KeywordSignalRule(
    name="agri_heat",
    trigger_keywords=(
        "폭염",
        "고온 피해",
        "가뭄",
        "생육 부진",
        "생육 지연",
        "늦더위",
        "고온으로",
        "작황 부진",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.MEDIUM,
    reason="폭염·가뭄 → 생육 부진, 중기 공급 감소",
    action_hint="고랭지 배추·무에 영향 큼",
)

AGRI_COLD = KeywordSignalRule(
    name="agri_cold",
    trigger_keywords=("냉해", "한파 피해", "서리 피해", "동해 피해", "저온 피해"),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="냉해·한파 → 출하 가능 물량 감소",
    action_hint="11월 가을배추·무 수확기 한파 기사 우선",
)

AGRI_DISEASE = KeywordSignalRule(
    name="agri_disease",
    trigger_keywords=(
        "무름병",
        "탄저병",
        "병해충",
        "뿌리혹병",
        "노균병",
        "바이러스병",
        "병해 확산",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.MEDIUM,
    reason="병해충 확산 → 상품성 저하·수확량 감소",
    action_hint="건고추 탄저병, 배추 무름병이 대표 사례",
)

AGRI_AREA_DOWN = KeywordSignalRule(
    name="agri_area_down",
    trigger_keywords=(
        "재배면적 감소",
        "재배 면적 감소",
        "면적 줄",
        "파종 감소",
        "정식 감소",
        "생산량 감소",
        "생산 감소 전망",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.MEDIUM,
    reason="재배면적·생산량 감소 → 순별 공급 수준 하락",
    action_hint="감소율(%)을 magnitude로 추출. KREI 관측 인용 기사 우선",
)

AGRI_SHIPMENT_DELAY = KeywordSignalRule(
    name="agri_shipment_delay",
    trigger_keywords=(
        "출하 지연",
        "출하지연",
        "수확 지연",
        "출하량 감소",
        "반입량 감소",
        "물량 부족",
        "품귀",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="출하 지연·반입 감소 → 즉시 공급 감소",
    action_hint="반입량 데이터(R01)와 교차 확인 후 사용",
)

# ---------------------------------------------------------------------------
# B. 공급 증가·수요 감소 (가격 하락 요인)
# ---------------------------------------------------------------------------

AGRI_RESERVE_RELEASE = KeywordSignalRule(
    name="agri_reserve_release",
    # "비축물량 1만톤 방출"처럼 단어 사이에 수량이 끼므로 "방출" 단독으로 잡는다.
    # 수매·비축 확대(공급 감소)는 별도 규칙 AGRI_RESERVE_BUY 로 분리.
    trigger_keywords=(
        "방출",
        "비축 공급",
        "비축물량",
        "비축 물량",
        "비축배추",
        "비축 배추",
        "정부 공급 확대",
        "공급 확대",
        "추가 공급",
        "공급량 확대",
        "푼다",
        "풀어",
        "물량 공급",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="정부 비축물량 방출 → 도매시장 공급 즉시 증가",
    action_hint="방출량(톤)을 가락 일 반입량과 비교해 magnitude 산정",
)

AGRI_RESERVE_BUY = KeywordSignalRule(
    name="agri_reserve_buy",
    trigger_keywords=(
        "수매 확대",
        "비축 확대",
        "정부 수매",
        "수매 물량 확대",
        "시장격리",
        "시장 격리",
        "산지 폐기",
    ),
    veto_keywords=POSTHOC_VETO + ("방출",),
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.SHORT,
    importance=Importance.HIGH,
    reason="정부 수매·시장격리·산지 폐기 → 시장 공급 감소",
    action_hint="수매량(톤)을 magnitude로 추출. 방출 기사와 혼동 주의",
)

AGRI_IMPORT_UP = KeywordSignalRule(
    name="agri_import_up",
    trigger_keywords=(
        "trq",
        "할당관세",
        "수입 확대",
        "수입물량 확대",
        "수입 증량",
        "증량",
        "관세 인하",
        "수입산 공급",
        "중국산 배추",
        "배추 수입",
        "수입 배추",
        "신선배추 수입",
        "수입산 배추",
        "조기 도입",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BEARISH,
    horizon=Horizon.LONG,
    importance=Importance.HIGH,
    reason="TRQ·할당관세·수입 → 공급 증가, 하락 요인 (2024년처럼 배추 수입도 발생)",
    action_hint="양파·깐마늘·건고추는 중기, 배추 수입은 단기 물량",
)

AGRI_GOOD_CROP = KeywordSignalRule(
    name="agri_good_crop",
    trigger_keywords=("작황 양호", "작황 호조", "풍작", "생산량 증가", "재배면적 증가", "면적 늘"),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BEARISH,
    horizon=Horizon.LONG,
    importance=Importance.LOW,
    reason="작황 양호·면적 증가 → 중기 공급 증가 (이미 가격에 반영된 경우 많음)",
    action_hint="과거 방향 적중률 낮음. 발동 가중 0.5",
)

AGRI_VOLUME_UP = KeywordSignalRule(
    name="agri_volume_up",
    trigger_keywords=(
        "출하 본격",
        "출하 시작",
        "출하량 증가",
        "반입량 증가",
        "물량 증가",
        "공급 확대",
        "홍수 출하",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="출하 본격화·반입 증가 → 즉시 공급 증가",
    action_hint="10월 하순 가을배추·무 출하 개시 기사가 전형",
)

AGRI_DISCOUNT_SUPPORT = KeywordSignalRule(
    name="agri_discount_support",
    trigger_keywords=(
        "할인 지원",
        "할인지원",
        "농산물 할인",
        "물가 안정 대책",
        "수급 안정 대책",
        "수급안정 대책",
        "가격 안정 대책",
    ),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BEARISH,
    horizon=Horizon.SHORT,
    importance=Importance.MEDIUM,
    reason="정부 수급·물가 대책 → 비축 방출·수입 동반, 소매 수요는 증가하나 도매는 공급 우위",
    action_hint="경제뉴스 트랙(D)에서 주로 잡힘. 농산물전반 scope",
)

# ---------------------------------------------------------------------------
# C. 수요 증가 (가격 상승 요인, 적중률 낮음)
# ---------------------------------------------------------------------------

AGRI_KIMJANG_DEMAND = KeywordSignalRule(
    name="agri_kimjang_demand",
    trigger_keywords=("김장 수요", "김장철 수요", "김장 성수기", "김장 앞두고", "김장 비용"),
    veto_keywords=POSTHOC_VETO,
    negation_keywords=_NO_NEG,
    direction=Direction.BULLISH,
    horizon=Horizon.LONG,
    importance=Importance.LOW,
    reason="김장 수요 전망 → 11월 중·하순 수요 증가 (계절성과 중복, 적중률 낮음)",
    action_hint="순별 예측의 계절 피처와 중복되므로 보정 가중 0.5",
    target_symbols=("배추", "무", "깐마늘", "건고추"),
)

AGRI_RULES: list[KeywordSignalRule] = [
    AGRI_TYPHOON,
    AGRI_HEAVY_RAIN,
    AGRI_HEAT,
    AGRI_COLD,
    AGRI_DISEASE,
    AGRI_AREA_DOWN,
    AGRI_SHIPMENT_DELAY,
    AGRI_RESERVE_RELEASE,
    AGRI_RESERVE_BUY,
    AGRI_IMPORT_UP,
    AGRI_GOOD_CROP,
    AGRI_VOLUME_UP,
    AGRI_DISCOUNT_SUPPORT,
    AGRI_KIMJANG_DEMAND,
]

# 발동 가중 (기획서 4-4: 과거 방향 적중률이 낮은 유형은 감액)
IMPORTANCE_WEIGHT: dict[Importance, float] = {
    Importance.HIGH: 1.0,
    Importance.MEDIUM: 0.8,
    Importance.LOW: 0.5,
}
