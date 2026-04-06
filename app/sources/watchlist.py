"""관심 종목 정의 모듈.

WatchedSymbol: 종목 코드 + 매칭 키워드 매핑
DEFAULT_WATCHLIST: 기본 관심 종목 목록

확장 방법:
  - 새 종목 추가: WatchedSymbol 항목을 DEFAULT_WATCHLIST에 추가
  - 외부 설정 파일 연동: load_watchlist_from_json() 같은 팩토리 함수 추가
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchedSymbol:
    """단일 관심 종목 정의.

    Attributes:
        symbol: 종목 코드 (예: "NVDA", "005930")
        keywords: 제목/요약에서 찾을 키워드 튜플. 소문자 기준.
    """

    symbol: str
    keywords: tuple[str, ...]


# ---------------------------------------------------------------------------
# 기본 관심 종목 목록
# 키워드는 소문자로 작성. 매칭 시 대상 텍스트를 소문자로 변환해 비교한다.
# ---------------------------------------------------------------------------

DEFAULT_WATCHLIST: list[WatchedSymbol] = [
    # --- 미국 빅테크 ---
    WatchedSymbol("NVDA",  ("nvidia",       "엔비디아",   "nvda")),
    WatchedSymbol("AAPL",  ("apple",        "애플",       "iphone", "아이폰")),
    WatchedSymbol("MSFT",  ("microsoft",    "마이크로소프트", "azure", "msft")),
    WatchedSymbol("AMZN",  ("amazon",       "아마존",     "aws",    "amzn")),
    WatchedSymbol("GOOGL", ("google",       "구글",       "alphabet", "gemini")),
    WatchedSymbol("META",  ("meta",         "메타",       "facebook", "페이스북", "instagram")),
    WatchedSymbol("TSLA",  ("tesla",        "테슬라",     "elon musk", "일론 머스크")),
    # --- 미국 반도체 ---
    WatchedSymbol("AMD",   ("amd",          "라이젠",     "radeon")),
    WatchedSymbol("INTC",  ("intel",        "인텔")),
    WatchedSymbol("QCOM",  ("qualcomm",     "퀄컴",       "snapdragon")),
    WatchedSymbol("ASML",  ("asml",         "극자외선", "euv")),
    # --- 한국 ADR ---
    WatchedSymbol("CPNG",  ("coupang",      "쿠팡",       "cpng")),
    # --- 한국 주식 (종목코드 사용) ---
    WatchedSymbol("035420", ("naver",       "네이버",     "라인")),
    WatchedSymbol("035720", ("kakao",       "카카오",     "카카오뱅크", "카카오페이")),
    WatchedSymbol("005930", ("삼성전자",    "samsung electronics", "갤럭시")),
    WatchedSymbol("000660", ("sk하이닉스",  "sk hynix",   "하이닉스")),
    WatchedSymbol("000270", ("기아",        "kia")),
    WatchedSymbol("005380", ("현대차",      "hyundai")),
    WatchedSymbol("051910", ("lg화학",      "lg chem")),
    WatchedSymbol("006400", ("삼성sdi",     "samsung sdi")),
]
