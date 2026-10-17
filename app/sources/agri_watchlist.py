"""해커톤 5품목 watchlist — 기존 WatchedSymbol / KeywordTagger를 그대로 재사용한다.

symbol 값이 article_symbols.symbol 에 기록되므로, 품목명을 그대로 symbol로 쓴다.
키워드는 소문자 substring 매칭이므로 짧은 단어는 오탐에 주의:
  - "무"  : 단독으로 쓰면 거의 모든 기사에 걸린다 → "가을무", "무 가격" 처럼 복합어만
  - "마늘": "깐마늘"·"마늘 가격" 등. "마늘종"은 제외
  - "고추": "건고추"·"고춧가루"·"홍고추"만. "고추장"·"청양고추"는 veto

수급 키워드(AND 조건)는 여기서 다루지 않는다. 품목 태깅은 넓게, 사건 판정은
agri_rules.py 의 KeywordSignalRule 이 좁게 한다.

AgriTagger: 기존 KeywordTagger(제목+요약 어디든 1회)는 요약문 한 줄 언급("…배추도 올랐다")에
걸려 오탐이 많았다 (2026-10-15 실측: 태깅 5건 중 2건 오탐). 제목에 키워드가 있거나,
요약에 2회 이상 나올 때만 태깅한다.
"""

import re

from app.sources.watchlist import WatchedSymbol

AGRI_WATCHLIST: list[WatchedSymbol] = [
    WatchedSymbol("배추", ("배추", "김장배추", "가을배추", "고랭지배추", "봄배추")),
    WatchedSymbol(
        "무",
        (
            "가을무",
            "김장무",
            "월동무",
            "고랭지무",
            "무 가격",
            "무 산지",
            "무 출하",
            "무값",
            "무 도매",
            "무 재배",
            "무 생산",
            "무 반입",
            "배추·무",
            "무·배추",
            "배추와 무",
            "배추, 무",
            "배추 무",
        ),
    ),
    WatchedSymbol("양파", ("양파", "저장양파", "햇양파")),
    WatchedSymbol(
        "깐마늘",
        (
            "깐마늘",
            "마늘 가격",
            "마늘값",
            "마늘 수입",
            "마늘 비축",
            "마늘 저장",
            "마늘 재배",
            "마늘 파종",
            "마늘 재고",
            "마늘 생산",
            "마늘 수매",
            "마늘·",
            "·마늘",
        ),
    ),
    WatchedSymbol(
        "건고추",
        (
            "건고추",
            "고춧가루",
            "홍고추",
            "고추 수확",
            "고추 수입",
            "고추 가격",
            "고추값",
            "고추 재배",
            "고추 생산",
            "고추 수매",
            "고추 작황",
            "탄저병",
        ),
    ),
]

# 품목 태깅 후 제외할 문맥 (요리·레시피·가공식품 기사)
AGRI_VETO_KEYWORDS: tuple[str, ...] = (
    "레시피",
    "요리법",
    "맛집",
    "고추장",
    "청양고추",
    "마늘종",
    "풋고추",
    "오이고추",
    "고추냉이",
    "김치찌개",
    "배추전",
    "양파링",
)


# 단독 '무' — 품목 나열 구분자(·,/、 공백 괄호) 사이에 한 글자로 올 때만.
# "무료"·"무게"·"무름병" 등은 제외
_MU_RE = re.compile(
    r"(?:^|[\s·,/、()\[\]\"'“”‘’])무(?=$|[\s·,/、()\[\]\"'“”‘’%값이가는을를도와과의])"
)


class AgriTagger:
    """제목 우선 품목 태거. SymbolTagger Protocol 구현 (KeywordTagger 와 교체 가능)."""

    def __init__(self, watchlist: list[WatchedSymbol] = AGRI_WATCHLIST, min_summary_hits: int = 2):
        self._watchlist = watchlist
        self._min = min_summary_hits

    @property
    def tagger_name(self) -> str:
        return "agri_keyword_v2"

    def tag(self, title: str, summary: str) -> list[str]:
        t, s = title.lower(), (summary or "").lower()
        if any(v in t or v in s for v in AGRI_VETO_KEYWORDS):
            return []
        out = []
        for w in self._watchlist:
            in_title = any(k in t for k in w.keywords)
            hits = sum(s.count(k) for k in w.keywords)
            if w.symbol == "무":  # 단독 '무'는 정규식으로 보강
                in_title = in_title or bool(_MU_RE.search(title))
                hits += len(_MU_RE.findall(summary or ""))
            if in_title or hits >= self._min:
                out.append(w.symbol)
        return out
