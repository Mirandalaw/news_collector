"""MorningBriefing → 텍스트 렌더러.

터미널에서 바로 읽을 수 있는 포맷으로 브리핑을 출력한다.

설계 원칙:
  - 섹션 헤더 / 아이템 / 구분선의 3계층 구조
  - 요약 줄은 들여쓰기로 시각적 계층 표현
  - URL은 마지막 줄에 배치 (읽기 흐름 방해 최소화)
  - 빈 섹션에는 "관련 뉴스가 없습니다." 메시지 표시
"""

from app.briefing.models import BriefingItem, BriefingSection, MorningBriefing
from app.signals.models import (
    DIRECTION_ICON,
    DIRECTION_LABEL,
    HORIZON_LABEL,
    IMPORTANCE_LABEL,
    Signal,
)

_WIDTH = 62
_THICK = "═" * _WIDTH
_THIN = "─" * _WIDTH
_BLANK = ""

_EVENT_TYPE_LABEL: dict[str, str] = {
    "rate": "금리",
    "oil": "유가",
    "earnings": "실적",
    "policy": "정책",
    "geopolitics": "지정학",
}


# ---------------------------------------------------------------------------
# 공개 함수
# ---------------------------------------------------------------------------


def render_text(briefing: MorningBriefing) -> str:
    """MorningBriefing을 사람이 읽기 좋은 텍스트로 변환한다.

    Args:
        briefing: 완성된 브리핑 객체

    Returns:
        줄바꿈으로 구성된 텍스트 문자열
    """
    lines: list[str] = []
    lines.extend(_render_header(briefing))
    lines.append(_BLANK)

    for section in briefing.sections:
        lines.extend(_render_section(section))
        lines.append(_BLANK)

    lines.extend(_render_footer(briefing))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 섹션별 렌더러
# ---------------------------------------------------------------------------


def _render_header(briefing: MorningBriefing) -> list[str]:
    date_str = briefing.since.strftime("%Y-%m-%d")
    since_str = briefing.since.strftime("%H:%M")
    until_str = briefing.until.strftime("%H:%M UTC")
    gen_str = briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC")

    return [
        _THICK,
        f"  아침 브리핑  |  {date_str}  ({since_str} ~ {until_str})",
        f"  생성: {gen_str}  |  총 {briefing.total_items}건",
        _THICK,
    ]


def _render_section(section: BriefingSection) -> list[str]:
    count_label = f"{section.count}건" if not section.is_empty else "없음"
    lines: list[str] = [
        f"{section.emoji}  [ {section.title} ]  {count_label}",
        _THIN,
    ]

    if section.is_empty:
        lines.append("  관련 뉴스가 없습니다.")
        return lines

    for idx, item in enumerate(section.items, 1):
        lines.extend(_render_item(idx, item))

    return lines


def _render_item(idx: int, item: BriefingItem) -> list[str]:
    lines: list[str] = []

    # 제목 줄: 번호 + 제목 + 종목 태그 + 이벤트 타입 태그
    sym_tag = f"  [{', '.join(item.symbols)}]" if item.symbols else ""
    event_tag = (
        f"  [{_EVENT_TYPE_LABEL.get(item.event_type, item.event_type)}]" if item.event_type else ""
    )
    lines.append(f"{idx:2d}. {item.title}{sym_tag}{event_tag}")

    # 메타 줄: 출처 + 그룹 정보 + 발행 시각
    time_part = ""
    if item.published_at:
        time_part = f"  ({item.published_at.strftime('%m/%d %H:%M')})"

    if item.article_count > 1:
        other_sources = item.sources[1:]  # 대표 소스 제외
        others_str = f" ({', '.join(other_sources)})" if other_sources else ""
        group_part = f"  +{item.article_count - 1}건{others_str}"
        lines.append(f"    출처: {item.source_name}{group_part}{time_part}")
    else:
        lines.append(f"    출처: {item.source_name}{time_part}")

    # 요약 줄 (들여쓰기)
    if item.summary_text:
        for summary_line in item.summary_text.splitlines():
            if summary_line.strip():
                lines.append(f"    › {summary_line.strip()}")

    # signal 블록 (최대 2개)
    if item.signals:
        for signal in item.signals[:2]:
            lines.extend(_render_signal(signal))

    # URL
    lines.append(f"    {item.url}")
    lines.append(_BLANK)

    return lines


def _render_signal(signal: Signal) -> list[str]:
    """Signal 1건을 2줄로 렌더링한다."""
    importance_label = IMPORTANCE_LABEL.get(signal.importance, str(signal.importance.value))
    direction_icon = DIRECTION_ICON.get(signal.direction, "?")
    direction_label = DIRECTION_LABEL.get(signal.direction, str(signal.direction.value))
    horizon_label = HORIZON_LABEL.get(signal.horizon, str(signal.horizon.value))

    return [
        f"    {importance_label} | {direction_icon} {direction_label} | {horizon_label}",
        f"    › {signal.reason}",
        f"    › [힌트] {signal.action_hint}",
    ]


def _render_footer(briefing: MorningBriefing) -> list[str]:
    non_empty = [s for s in briefing.sections if not s.is_empty]
    section_summary = "  ".join(f"{s.emoji} {s.title} {s.count}건" for s in non_empty)
    return [
        _THIN,
        f"  {section_summary}" if section_summary else "  결과 없음",
        _THIN,
    ]
