"""BriefingResult → MorningBriefing 변환 모듈.

DB 조회 원시 결과(BriefingResult)를 브리핑 표시 모델(MorningBriefing)로 변환한다.

변환 규칙:
  - symbol_section은 market과 중복된 기사를 제외한 deduplicated_symbol_news를 사용
  - title_hash exact match 기준으로 기사를 그룹핑 (같은 이슈 → 1개 BriefingItem)
  - title_hash가 None/빈문자열/공백이면 단독 그룹 처리
  - 그룹 내 대표 기사 선정: source 우선순위 → published_at → summary 길이 → collected_at
  - signal은 그룹 내 전체 기사에서 수집, rule_name 중복 제거 후 importance 내림차순
  - summary_text: ai_summary가 있으면 우선 사용, 없으면 원본 summary 사용
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.briefing.models import BriefingItem, BriefingSection, MorningBriefing
from app.db.repositories.briefing_repository import BriefingArticle
from app.services.briefing_service import BriefingResult
from app.signals.models import Importance, Signal, SignalReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 소스 우선순위 (낮은 숫자 = 더 높은 우선순위)
# ---------------------------------------------------------------------------

_SOURCE_PRIORITY: dict[str, int] = {
    "한국경제": 0,
    "한국경제_증권": 0,
    "한국경제_IT": 0,
    "한국경제_국제": 0,
    "매일경제": 1,
    "매일경제_주식": 1,
    "매일경제_IT": 1,
    "매일경제_국제": 1,
    "전자신문": 2,
    "전자신문_ICT": 2,
}
_DEFAULT_SOURCE_PRIORITY = 99

# importance 정렬 기준
_IMPORTANCE_ORDER: dict[str, int] = {
    Importance.HIGH.value: 0,
    Importance.MEDIUM.value: 1,
    Importance.LOW.value: 2,
}


# ---------------------------------------------------------------------------
# 공개 함수
# ---------------------------------------------------------------------------


def build_morning_briefing(
    result: BriefingResult,
    signal_report: SignalReport | None = None,
) -> MorningBriefing:
    """BriefingResult + SignalReport를 MorningBriefing으로 변환한다.

    Args:
        result: BriefingService.run()의 반환값
        signal_report: SignalEngine.analyze()의 반환값. None이면 빈 SignalReport 사용.

    Returns:
        섹션별로 정리된 MorningBriefing
    """
    _report = signal_report or SignalReport(
        analyzed_at=datetime.now(timezone.utc),
        briefing_since=result.query.since,
        briefing_until=result.query.until,
    )
    signal_map = _build_signal_map(_report)

    market_section = BriefingSection(
        title="오늘 시장",
        emoji="📈",
        items=_group_and_build(result.market_news, signal_map),
    )
    symbol_section = BriefingSection(
        title="내 종목 뉴스",
        emoji="🔍",
        items=_group_and_build(result.deduplicated_symbol_news, signal_map),
    )
    event_section = BriefingSection(
        title="오늘 체크할 이벤트",
        emoji="📅",
        items=_group_and_build(result.event_news, signal_map),
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
# 신규 내부 함수
# ---------------------------------------------------------------------------


def _build_signal_map(signal_report: SignalReport) -> dict[int, list[Signal]]:
    """SignalReport를 {article_id: [Signal, ...]} dict로 변환한다."""
    result: dict[int, list[Signal]] = defaultdict(list)
    for signal in signal_report.signals:
        result[signal.article_id].append(signal)
    return dict(result)


def _is_valid_hash(title_hash: str) -> bool:
    """title_hash가 그룹핑에 사용 가능한지 검증한다.

    None은 호출 전 빈문자열로 정규화되어 들어오므로 strip()만 검사한다.
    """
    return bool(title_hash and title_hash.strip())


def _group_by_title_hash(
    articles: list[BriefingArticle],
) -> list[list[BriefingArticle]]:
    """title_hash exact match 기준으로 기사를 그룹핑한다.

    - 유효한 hash가 동일한 기사 → 같은 그룹
    - 유효하지 않은 hash(None/빈문자열/공백) → 각각 단독 그룹
    - 그룹 순서 = 해당 hash의 첫 번째 기사가 입력 리스트에서 등장한 순서
    """
    # 순서 보존을 위해 OrderedDict 대신 list + dict 조합 사용
    hash_to_group: dict[str, list[BriefingArticle]] = {}
    order: list[str] = []  # 첫 등장 순서 기록 (단독 그룹은 고유 키 사용)
    solo_counter = 0

    for article in articles:
        if _is_valid_hash(article.title_hash):
            key = article.title_hash
            if key not in hash_to_group:
                hash_to_group[key] = []
                order.append(key)
            hash_to_group[key].append(article)
        else:
            # 단독 그룹: 고유 키로 등록 (다른 단독 기사와 절대 합쳐지지 않음)
            solo_key = f"__solo_{solo_counter}__"
            solo_counter += 1
            hash_to_group[solo_key] = [article]
            order.append(solo_key)

    return [hash_to_group[k] for k in order]


def _pick_representative(
    group: list[BriefingArticle],
    signal_map: dict[int, list[Signal]],
) -> BriefingArticle:
    """그룹 내에서 대표 기사 1건을 선정한다.

    우선순위 (앞 조건 동점 시 다음 적용):
      1. _SOURCE_PRIORITY (낮은 숫자 우선)
      2. published_at 오름차순 (None은 최하위)
      3. len(summary) 내림차순
      4. collected_at 오름차순 (fallback)

    signal 보유 여부는 기준에 포함하지 않는다.
    """
    _epoch = datetime.fromtimestamp(0, tz=timezone.utc)
    _max_dt = datetime(9999, 12, 31, tzinfo=timezone.utc)

    def sort_key(a: BriefingArticle) -> tuple:
        source_rank = _SOURCE_PRIORITY.get(a.source_name, _DEFAULT_SOURCE_PRIORITY)
        pub_dt = a.published_at if a.published_at is not None else _max_dt
        summary_len = -len(a.summary)  # 내림차순 → 부호 반전
        return (source_rank, pub_dt, summary_len, a.collected_at)

    return min(group, key=sort_key)


def _collect_signals(
    group: list[BriefingArticle],
    signal_map: dict[int, list[Signal]],
) -> list[Signal]:
    """그룹 내 모든 기사에서 signal을 수집한다.

    - rule_name 중복 제거 (그룹 내 기사 순서 기준, 첫 번째 유지)
    - importance 내림차순(HIGH → MEDIUM → LOW) 정렬
    """
    seen_rules: set[str] = set()
    collected: list[Signal] = []

    for article in group:
        for signal in signal_map.get(article.id, []):
            if signal.rule_name not in seen_rules:
                seen_rules.add(signal.rule_name)
                collected.append(signal)

    collected.sort(key=lambda s: _IMPORTANCE_ORDER.get(s.importance.value, 9))
    return collected


def _group_sources(
    representative: BriefingArticle,
    group: list[BriefingArticle],
) -> list[str]:
    """그룹 내 source_name을 중복 제거해 반환한다.

    대표 기사의 source_name을 첫 번째로 유지하고 나머지를 이어 붙인다.
    """
    seen: set[str] = {representative.source_name}
    sources: list[str] = [representative.source_name]
    for article in group:
        if article.source_name not in seen:
            seen.add(article.source_name)
            sources.append(article.source_name)
    return sources


def _to_item_from_group(
    representative: BriefingArticle,
    group: list[BriefingArticle],
    signals: list[Signal],
) -> BriefingItem:
    """대표 기사 + 그룹 메타 + signal을 BriefingItem으로 조립한다."""
    summary_text = (
        representative.ai_summary if representative.ai_summary else representative.summary
    )
    sources = _group_sources(representative, group)

    return BriefingItem(
        article_id=representative.id,
        title=representative.title,
        source_name=representative.source_name,
        url=representative.url,
        summary_text=summary_text,
        symbols=list(representative.symbols),
        published_at=representative.published_at,
        signals=signals,
        article_count=len(group),
        sources=sources,
    )


def _group_and_build(
    articles: list[BriefingArticle],
    signal_map: dict[int, list[Signal]],
) -> list[BriefingItem]:
    """기사 리스트를 그룹핑해 BriefingItem 목록으로 변환한다.

    빈 리스트 입력 시 빈 리스트 반환.
    """
    if not articles:
        return []

    groups = _group_by_title_hash(articles)
    items: list[BriefingItem] = []

    for group in groups:
        representative = _pick_representative(group, signal_map)
        signals = _collect_signals(group, signal_map)
        item = _to_item_from_group(representative, group, signals)
        items.append(item)

    logger.debug(
        "_group_and_build | 입력=%d건 → 그룹=%d개",
        len(articles),
        len(items),
    )
    return items


# ---------------------------------------------------------------------------
# 기존 함수 유지 (하위 호환)
# ---------------------------------------------------------------------------


def _to_items(articles: list[BriefingArticle]) -> list[BriefingItem]:
    return [_to_item(a) for a in articles]


def _to_item(a: BriefingArticle) -> BriefingItem:
    """BriefingArticle → BriefingItem 변환 (signal/그룹 없음).

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
