"""BriefingResult → MorningBriefing 변환 모듈.

DB 조회 원시 결과(BriefingResult)를 브리핑 표시 모델(MorningBriefing)로 변환한다.

변환 규칙:
  - symbol_section은 market과 중복된 기사를 제외한 deduplicated_symbol_news를 사용
  - summary_text: ai_summary가 있으면 우선 사용, 없으면 원본 summary 사용
  - 발행 시각 없는 기사는 published_at=None 그대로 유지
"""

from datetime import datetime, timezone

from app.briefing.models import BriefingItem, BriefingSection, MorningBriefing
from app.db.repositories.briefing_repository import BriefingArticle
from app.services.briefing_service import BriefingResult


def build_morning_briefing(result: BriefingResult) -> MorningBriefing:
    """BriefingResult를 MorningBriefing으로 변환한다.

    Args:
        result: BriefingService.run()의 반환값

    Returns:
        섹션별로 정리된 MorningBriefing
    """
    market_section = BriefingSection(
        title="오늘 시장",
        emoji="📈",
        items=_to_items(result.market_news),
    )
    symbol_section = BriefingSection(
        title="내 종목 뉴스",
        emoji="🔍",
        items=_to_items(result.deduplicated_symbol_news),
    )
    event_section = BriefingSection(
        title="오늘 체크할 이벤트",
        emoji="📅",
        items=_to_items(result.event_news),
    )

    return MorningBriefing(
        generated_at=datetime.now(timezone.utc),
        since=result.query.since,
        until=result.query.until,
        market_section=market_section,
        symbol_section=symbol_section,
        event_section=event_section,
    )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _to_items(articles: list[BriefingArticle]) -> list[BriefingItem]:
    return [_to_item(a) for a in articles]


def _to_item(a: BriefingArticle) -> BriefingItem:
    """BriefingArticle → BriefingItem 변환.

    ai_summary가 비어 있으면 원본 summary를 summary_text로 사용한다.
    """
    summary_text = a.ai_summary if a.ai_summary else a.summary
    return BriefingItem(
        article_id=a.id,
        title=a.title,
        source_name=a.source_name,
        url=a.url,
        summary_text=summary_text,
        symbols=list(a.symbols),
        published_at=a.published_at,
    )
