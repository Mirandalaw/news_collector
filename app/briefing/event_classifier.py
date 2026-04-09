"""기사 제목 기반 이벤트 타입 분류 모듈.

classify_event_type(title) → str | None

지원 타입:
  rate        금리/통화정책
  oil         유가/에너지
  earnings    실적/가이던스
  policy      관세/재정/무역정책
  geopolitics 지정학/분쟁

우선순위: 리스트 순서대로 첫 번째 매칭 타입을 반환한다.
매칭 없으면 None 반환.
"""

from __future__ import annotations

_RATE_KEYWORDS: tuple[str, ...] = (
    "기준금리",
    "fomc",
    "연준",
    "금리 인하",
    "금리인하",
    "금리 인상",
    "금리인상",
    "금리 동결",
    "통화정책",
    "한은 금리",
    "한국은행 금리",
    "피벗",
    "pivot",
    "빅컷",
    "인하 시사",
    "인상 시사",
)

_OIL_KEYWORDS: tuple[str, ...] = (
    "국제유가",
    "wti",
    "브렌트",
    "brent",
    "opec",
    "산유국",
    "원유",
)

_EARNINGS_KEYWORDS: tuple[str, ...] = (
    "실적 발표",
    "실적발표",
    "분기 실적",
    "실적 시즌",
    "어닝 시즌",
    "어닝 서프라이즈",
    "어닝 쇼크",
    "실적 서프라이즈",
    "실적 쇼크",
    "영업이익",
    "가이던스",
)

_POLICY_KEYWORDS: tuple[str, ...] = (
    "관세",
    "tariff",
    "무역 협상",
    "재정 정책",
    "경기 부양",
    "부양책",
    "법안 통과",
    "정책 발표",
    "제재 조치",
)

_GEOPOLITICS_KEYWORDS: tuple[str, ...] = (
    "지정학",
    "북한",
    "중동",
    "러시아",
    "우크라이나",
    "대만 해협",
    "이스라엘",
    "하마스",
    "나토",
    "nato",
)

# (event_type, keywords) — 순서대로 우선순위 적용
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rate", _RATE_KEYWORDS),
    ("oil", _OIL_KEYWORDS),
    ("earnings", _EARNINGS_KEYWORDS),
    ("policy", _POLICY_KEYWORDS),
    ("geopolitics", _GEOPOLITICS_KEYWORDS),
)


def classify_event_type(title: str) -> str | None:
    """기사 제목에서 이벤트 타입을 분류한다.

    Args:
        title: 기사 제목

    Returns:
        이벤트 타입 문자열 (rate / oil / earnings / policy / geopolitics)
        매칭 없으면 None
    """
    text = title.lower()
    for event_type, keywords in _RULES:
        if any(kw in text for kw in keywords):
            return event_type
    return None
