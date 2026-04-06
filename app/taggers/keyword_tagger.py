"""종목 태깅 인터페이스 및 키워드 기반 구현체.

SymbolTagger Protocol을 구현한 객체를 NewsIngestionService에 주입해
태깅 전략을 교체 가능하게 한다.

현재 구현체:
  KeywordTagger - WatchedSymbol의 키워드를 기사 텍스트에서 substring 검색

확장 방법:
  SymbolTagger Protocol을 구현하는 새 클래스 작성 후 주입.
  예: AiSymbolTagger(client=openai_client, model="gpt-4o")
"""

import logging
from typing import Protocol

from app.sources.watchlist import WatchedSymbol

logger = logging.getLogger(__name__)


class SymbolTagger(Protocol):
    """종목 태깅 인터페이스.

    tag() 메서드 하나만 구현하면 어떤 전략이든 주입 가능하다.
    (rule-based, ML, LLM 등)
    """

    @property
    def tagger_name(self) -> str:
        """tagged_by 컬럼에 기록할 분류기 이름."""
        ...

    def tag(self, title: str, summary: str) -> list[str]:
        """기사 텍스트에서 관련 종목 코드 목록을 반환한다.

        Args:
            title: 기사 제목
            summary: 기사 요약

        Returns:
            매칭된 종목 코드 목록. 중복 없음, 빈 리스트 가능.
        """
        ...


class KeywordTagger:
    """키워드 substring 매칭 기반 종목 태거.

    watchlist의 각 WatchedSymbol 키워드를 (title + summary) 텍스트에서
    대소문자 무시 substring 검색으로 찾는다.

    한계:
      - 오탐 가능 (예: "meta" → "metadata" 포함)
      - 문맥 구분 불가
      → 정밀도가 필요하면 SymbolTagger Protocol 구현체를 교체할 것

    Args:
        watchlist: 매칭 대상 WatchedSymbol 목록
    """

    def __init__(self, watchlist: list[WatchedSymbol]) -> None:
        self._watchlist = watchlist

    @property
    def tagger_name(self) -> str:
        return "keyword"

    def tag(self, title: str, summary: str) -> list[str]:
        """title과 summary를 합친 텍스트에서 키워드를 검색해 종목 코드를 반환한다."""
        text = f"{title} {summary}".lower()
        matched: list[str] = []

        for watched in self._watchlist:
            if any(keyword in text for keyword in watched.keywords):
                matched.append(watched.symbol)
                logger.debug(
                    "태깅 매칭 | symbol=%s | title=%.40s",
                    watched.symbol,
                    title,
                )

        return matched
