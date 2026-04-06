"""아침 브리핑 표시 모델.

BriefingResult(DB 조회 원시 데이터)를 화면 출력에 적합한 구조로 변환한 DTO.

계층:
  BriefingItem    : 기사 1건 (ai_summary 우선 적용된 summary_text 포함)
  BriefingSection : 섹션 1개 (제목 + 아이템 목록)
  MorningBriefing : 최종 브리핑 (메타데이터 + 3개 섹션)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # 순환 임포트 방지용


# ---------------------------------------------------------------------------
# 기사 단위
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BriefingItem:
    """브리핑에 표시되는 기사 1건.

    Attributes:
        article_id: DB primary key
        title: 기사 제목
        source_name: 뉴스 소스
        url: 원문 URL
        summary_text: 표시용 요약 (ai_summary 우선, 없으면 원본 summary)
        symbols: 매칭된 종목 코드 목록
        published_at: 기사 발행 시각 (없을 수 있음)
    """

    article_id: int
    title: str
    source_name: str
    url: str
    summary_text: str
    symbols: list[str] = field(default_factory=list)
    published_at: datetime | None = None


# ---------------------------------------------------------------------------
# 섹션 단위
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BriefingSection:
    """브리핑 섹션 1개 (시장 / 종목 / 이벤트).

    Attributes:
        title: 섹션 제목 (예: "오늘 시장")
        emoji: 섹션 아이콘
        items: 해당 섹션 기사 목록
    """

    title: str
    emoji: str
    items: list[BriefingItem] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    @property
    def count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "count": self.count,
            "items": [_item_to_dict(i) for i in self.items],
        }


# ---------------------------------------------------------------------------
# 브리핑 최상위
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MorningBriefing:
    """아침 브리핑 완성 결과.

    Attributes:
        generated_at: 브리핑 생성 시각 (UTC)
        since: 조회 시작 시각
        until: 조회 종료 시각
        market_section: 시장/거시경제 섹션
        symbol_section: 관심 종목 섹션 (market 중복 제외)
        event_section: 이벤트/일정 섹션
    """

    generated_at: datetime
    since: datetime
    until: datetime
    market_section: BriefingSection
    symbol_section: BriefingSection
    event_section: BriefingSection

    @property
    def sections(self) -> list[BriefingSection]:
        return [self.market_section, self.symbol_section, self.event_section]

    @property
    def total_items(self) -> int:
        return sum(s.count for s in self.sections)

    def to_text(self) -> str:
        """사람이 읽기 좋은 텍스트 브리핑을 반환한다."""
        from app.briefing.renderer import render_text
        return render_text(self)

    def to_dict(self) -> dict:
        """JSON 직렬화 가능한 dict를 반환한다."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "since": self.since.isoformat(),
            "until": self.until.isoformat(),
            "total_items": self.total_items,
            "sections": {
                "market": self.market_section.to_dict(),
                "symbol": self.symbol_section.to_dict(),
                "event":  self.event_section.to_dict(),
            },
        }


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _item_to_dict(item: BriefingItem) -> dict:
    return {
        "article_id": item.article_id,
        "title": item.title,
        "source_name": item.source_name,
        "url": item.url,
        "summary_text": item.summary_text,
        "symbols": item.symbols,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }
