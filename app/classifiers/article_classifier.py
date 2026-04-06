"""기사 의미 분류 인터페이스 및 키워드 기반 구현체.

ArticleClassifier Protocol을 구현한 객체를 NewsIngestionService에 주입해
분류 전략을 교체 가능하게 한다.

분류 레이블:
  "market"  - 거시경제 / 지수 / 원자재 / 환율 수준 뉴스
  "company" - 개별 기업 행위 (실적, 계약, 규제, M&A, 배당)
  "event"   - 발표 일정 / 예정 이벤트 (earnings calendar, IPO 일정 등)
  "general" - 위 기준 미해당 (폴백)

우선순위: event > company > market > general
  가장 구체적인(event)을 먼저 검사해 오분류를 줄인다.

확장 방법:
  ArticleClassifier Protocol을 구현하는 새 클래스 작성 후 서비스에 주입.
  예: AiArticleClassifier(client=anthropic_client, model="claude-haiku-4-5")
"""

import logging
from typing import Literal, Protocol

logger = logging.getLogger(__name__)

ArticleType = Literal["market", "company", "event", "general"]

# ---------------------------------------------------------------------------
# 키워드 집합
# 소문자 기준. 매칭 시 title+summary를 lower()한 뒤 substring 검색.
# ---------------------------------------------------------------------------

# event: 일정/예정/달력 성격의 단어가 포함될 때
_EVENT_KEYWORDS: frozenset[str] = frozenset({
    # 영문
    "earnings calendar", "earnings schedule", "earnings date",
    "economic calendar", "event calendar",
    "ipo date", "ipo schedule", "goes public", "set to report",
    "upcoming earnings", "expected to report",
    "fomc meeting date", "fomc schedule",
    # 국문
    "실적 발표 일정", "발표 일정", "발표 예정", "발표예정",
    "상장 일정", "공모 일정", "청약 일정",
    "일정 공개", "일정 발표",
})

# company: 개별 기업 행위 (과거/현재 사실 위주)
_COMPANY_KEYWORDS: frozenset[str] = frozenset({
    # 실적/가이던스
    "earnings", "실적", "revenue", "매출", "영업이익", "순이익",
    "eps", "guidance", "가이던스", "beat", "miss", "어닝",
    "분기 실적", "연간 실적", "quarterly results",
    # 계약/딜
    "계약", "contract", "deal", "partnership",
    "인수", "acquisition", "merger", "m&a", "합병", "매각", "지분 취득",
    # 규제/법률
    "규제", "regulation", "제재", "sanctions",
    "lawsuit", "소송", "벌금", "fine", "조사", "investigation",
    "antitrust", "ftc", "공정위",
    # 주주환원
    "배당", "dividend", "buyback", "자사주", "주주환원",
    # 경영진
    "ceo", "cfo", "cto", "임원 교체", "대표 교체",
})

# market: 거시경제 / 지수 / 원자재 / 환율
_MARKET_KEYWORDS: frozenset[str] = frozenset({
    # 금리/통화정책
    "금리", "interest rate", "rate hike", "rate cut", "기준금리",
    "monetary policy", "통화정책",
    # 인플레이션
    "cpi", "inflation", "인플레이션", "물가", "pce", "ppi",
    # 중앙은행
    "fomc", "federal reserve", "연준", "파월", "powell", "한국은행", "ecb",
    # 채권/국채
    "국채", "treasury", "bond yield", "채권금리", "10년물", "2년물",
    # 원자재/에너지
    "유가", "oil price", "wti", "brent", "원유", "천연가스", "natural gas",
    "금값", "gold price", "구리",
    # 환율/달러
    "환율", "원달러", "달러 인덱스", "dollar index", "usdkrw", "위안",
    # 거시경제
    "gdp", "경기침체", "recession", "실업률", "unemployment", "고용지표",
    "무역수지", "trade balance", "경상수지",
    # 증시 지수
    "코스피", "코스닥", "s&p 500", "s&p500", "nasdaq", "dow jones",
    "russell", "nikkei", "항셍", "hang seng", "상해종합",
    # 변동성
    "vix", "공포지수",
})


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ArticleClassifier(Protocol):
    """기사 분류 인터페이스.

    classify() 메서드 하나만 구현하면 rule-based, ML, LLM 등 어떤 구현체든 주입 가능.
    """

    @property
    def classifier_name(self) -> str:
        """분류기 식별 이름. DB 기록용."""
        ...

    def classify(self, title: str, summary: str) -> ArticleType:
        """기사를 분류하고 ArticleType 레이블을 반환한다.

        Args:
            title: 기사 제목
            summary: 기사 요약

        Returns:
            "market" | "company" | "event" | "general"
        """
        ...


# ---------------------------------------------------------------------------
# 구현체
# ---------------------------------------------------------------------------

class KeywordArticleClassifier:
    """키워드 substring 매칭 기반 기사 분류기.

    title + summary 텍스트에서 keyword set을 우선순위 순서로 검색한다.

      event > company > market > general

    한계:
      - 문맥 없는 단순 매칭 (오분류 가능)
      - 정밀도가 필요하면 ArticleClassifier Protocol 구현체를 교체할 것
    """

    @property
    def classifier_name(self) -> str:
        return "keyword"

    def classify(self, title: str, summary: str) -> ArticleType:
        """title과 summary를 합친 소문자 텍스트에서 키워드를 검색해 분류한다."""
        text = f"{title} {summary}".lower()

        if self._matches(text, _EVENT_KEYWORDS):
            result: ArticleType = "event"
        elif self._matches(text, _COMPANY_KEYWORDS):
            result = "company"
        elif self._matches(text, _MARKET_KEYWORDS):
            result = "market"
        else:
            result = "general"

        logger.debug(
            "분류 결과 | type=%s | title=%.50s",
            result,
            title,
        )
        return result

    @staticmethod
    def _matches(text: str, keywords: frozenset[str]) -> bool:
        return any(kw in text for kw in keywords)
