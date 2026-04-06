"""중복 기사 필터 인터페이스 및 구현체.

DuplicateFilter Protocol을 구현한 객체를 NewsIngestionService에 주입해
중복 제거 정책을 교체 가능하게 한다.

현재 제공 구현체:
  NullDuplicateFilter  - 아무것도 하지 않음. URL dedup은 DB에서 처리 (기본값)
  TitleHashFilter      - 동일 세션 내 title_hash 기반 in-memory 중복 제거

확장 방법:
  DB 조회 기반 영속 중복 제거가 필요하면 DuplicateFilter Protocol을 구현한
  새 클래스를 추가하고 NewsIngestionService 생성 시 주입한다.
"""

import logging
from typing import Protocol

from app.db.repositories.news_repository import NewsArticle

logger = logging.getLogger(__name__)


class DuplicateFilter(Protocol):
    """중복 여부를 판단하는 필터 인터페이스."""

    def is_duplicate(self, article: NewsArticle) -> bool:
        """기사가 중복인지 여부를 반환한다."""
        ...

    def mark_seen(self, article: NewsArticle) -> None:
        """기사를 '이미 처리됨'으로 기록한다."""
        ...


class NullDuplicateFilter:
    """No-op 필터.

    URL 중복 제거는 DB의 UNIQUE 제약에 위임한다.
    기본값으로 사용하며, 기존 동작을 변경하지 않는다.
    """

    def is_duplicate(self, article: NewsArticle) -> bool:
        return False

    def mark_seen(self, article: NewsArticle) -> None:
        pass


class TitleHashFilter:
    """title_hash 기반 in-memory 중복 필터.

    동일 세션(run() 1회) 내에서 같은 타이틀의 기사가 여러 소스에서
    수집될 때 첫 번째만 저장하고 나머지를 skip한다.

    한계:
      - 세션이 종료되면 초기화됨 (영속 중복 제거 불가)
      - 영속 중복 제거가 필요하면 DB에서 기존 title_hash를 조회하는
        구현체로 교체해야 한다.
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, article: NewsArticle) -> bool:
        if not article.title_hash:
            return False
        return article.title_hash in self._seen

    def mark_seen(self, article: NewsArticle) -> None:
        if article.title_hash:
            self._seen.add(article.title_hash)
