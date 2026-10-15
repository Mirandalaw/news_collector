"""해커톤 5품목 watchlist — 기존 WatchedSymbol / KeywordTagger를 그대로 재사용한다.

symbol 값이 article_symbols.symbol 에 기록되므로, 품목명을 그대로 symbol로 쓴다.
키워드는 소문자 substring 매칭이므로 짧은 단어는 오탐에 주의:
  - "무"  : 단독으로 쓰면 거의 모든 기사에 걸린다 → "가을무", "무 가격" 처럼 복합어만
  - "마늘": "깐마늘"·"마늘 가격" 등. "마늘종"은 제외
  - "고추": "건고추"·"고춧가루"·"홍고추"만. "고추장"·"청양고추"는 veto

수급 키워드(AND 조건)는 여기서 다루지 않는다. 품목 태깅은 넓게, 사건 판정은
agri_rules.py 의 KeywordSignalRule 이 좁게 한다.
"""

from app.sources.watchlist import WatchedSymbol

AGRI_WATCHLIST: list[WatchedSymbol] = [
    WatchedSymbol("배추", ("배추", "김장배추", "가을배추", "고랭지배추", "봄배추", "포기")),
    WatchedSymbol("무", ("가을무", "김장무", "월동무", "무 가격", "무 산지", "무 출하", "무값", "무 도매")),
    WatchedSymbol("양파", ("양파", "저장양파", "햇양파")),
    WatchedSymbol("깐마늘", ("깐마늘", "마늘 가격", "마늘값", "마늘 수입", "마늘 비축", "마늘 저장", "마늘 재배", "마늘 파종")),
    WatchedSymbol("건고추", ("건고추", "고춧가루", "홍고추", "고추 수확", "고추 수입", "고추 가격", "고추값", "고추 재배")),
]

# 품목 태깅 후 제외할 문맥 (요리·레시피·가공식품 기사)
AGRI_VETO_KEYWORDS: tuple[str, ...] = (
    "레시피",
    "요리법",
    "맛집",
    "고추장",
    "청양고추",
    "마늘종",
    "김치찌개",
    "배추전",
    "양파링",
)
