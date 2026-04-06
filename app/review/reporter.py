"""검수 리포트 렌더러.

render_text()  → 사람이 읽기 쉬운 텍스트 (콘솔/파일)
render_json()  → 구조화된 JSON 문자열 (파일 저장 / 파이프라인 연동)
"""

import json
from datetime import datetime, timezone

from app.review.models import (
    ISSUE_LABEL,
    ArticleIssue,
    IssueKind,
    ReviewArticle,
    ReviewResult,
)

# 출력 폭 상수
_W = 66
_THICK = "═" * _W
_THIN = "─" * _W

# article_type 출력 순서
_TYPE_ORDER = ["market", "event", "company", "general"]


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def render_text(result: ReviewResult) -> str:
    """ReviewResult를 사람이 읽기 쉬운 텍스트로 렌더링한다."""
    parts: list[str] = []
    parts.append(_render_header(result))
    parts.append(_render_issue_summary(result))
    parts.append(_render_article_sections(result))
    if result.issues:
        parts.append(_render_issue_detail(result))
    parts.append(_render_footer(result))
    return "\n".join(parts)


def render_json(result: ReviewResult) -> str:
    """ReviewResult를 JSON 문자열로 변환한다."""
    data = {
        "generated_at": _now_kst_str(),
        "since": result.since.isoformat(),
        "until": result.until.isoformat(),
        "stats": result.stats,
        "total_articles": len(result.articles),
        "total_issues": len(result.issues),
        "issues_by_kind": {kind.value: len(items) for kind, items in result.issues_by_kind.items()},
        "articles": [_article_to_dict(a, result) for a in result.articles],
        "issues": [_issue_to_dict(i) for i in result.issues],
    }
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# 텍스트 렌더러 내부 구현
# ---------------------------------------------------------------------------


def _render_header(result: ReviewResult) -> str:
    since_str = _fmt_dt(result.since)
    until_str = _fmt_dt(result.until)
    stats = result.stats
    stat_parts = "  ".join(f"{t}:{stats.get(t, 0)}" for t in _TYPE_ORDER if stats.get(t, 0) > 0)
    lines = [
        _THICK,
        f"  검수 리포트  │  {since_str} ~ {until_str}",
        f"  전체: {len(result.articles)}건  │  {stat_parts}",
        _THICK,
    ]
    return "\n".join(lines)


def _render_issue_summary(result: ReviewResult) -> str:
    if not result.issues:
        return f"\n  ✓ 이슈 없음 — 전체 {len(result.articles)}건 정상\n"

    by_kind = result.issues_by_kind
    lines = ["", f"┌─ 발견된 이슈 ({len(result.issues)}건) " + "─" * (_W - 14) + "┐"]
    for kind in IssueKind:
        items = by_kind.get(kind, [])
        if items:
            label = ISSUE_LABEL[kind]
            count_str = f"{len(items)}건"
            content = f"│  {kind.value:<22}  {count_str:<5}  {label}"
            lines.append(content.ljust(_W + 1) + "│")
    lines.append("└" + "─" * _W + "┘")
    return "\n".join(lines)


def _render_article_sections(result: ReviewResult) -> str:
    by_type = result.articles_by_type
    issue_map = _build_issue_map(result.issues)
    parts: list[str] = []

    for atype in _TYPE_ORDER:
        articles = by_type.get(atype, [])
        if not articles:
            continue
        parts.append(f"\n{_THIN}")
        parts.append(f"  [{atype.upper()}]  {len(articles)}건")
        parts.append(_THIN)
        for idx, a in enumerate(articles, 1):
            parts.append(_render_article_row(idx, a, issue_map.get(a.id, [])))

    # _TYPE_ORDER에 없는 타입 처리 (확장 대비)
    known = set(_TYPE_ORDER)
    for atype, articles in by_type.items():
        if atype in known:
            continue
        parts.append(f"\n{_THIN}")
        parts.append(f"  [{atype.upper()}]  {len(articles)}건")
        parts.append(_THIN)
        for idx, a in enumerate(articles, 1):
            parts.append(_render_article_row(idx, a, issue_map.get(a.id, [])))

    return "\n".join(parts)


def _render_article_row(idx: int, a: ReviewArticle, issues: list[ArticleIssue]) -> str:
    time_str = _fmt_time(a.published_at or a.collected_at)
    sym_str = f"  [{','.join(a.symbols)}]" if a.symbols else ""
    title_line = f"  {idx:>3}. {a.title[:56]}"
    if len(a.title) > 56:
        title_line += "…"

    meta = f"       출처: {a.source_name}  │  {time_str}{sym_str}"

    lines = [title_line, meta]

    # 요약 (최대 2줄)
    if a.summary.strip():
        summary_preview = a.summary.replace("\n", " ").strip()
        if len(summary_preview) > 100:
            summary_preview = summary_preview[:100] + "…"
        lines.append(f"       › {summary_preview}")
    else:
        lines.append("       › (요약 없음)")

    # 이슈 인라인 표시
    for issue in issues:
        lines.append(f"       ⚠  [{issue.kind.value}] {issue.detail}")

    lines.append("")  # 빈 줄 구분
    return "\n".join(lines)


def _render_issue_detail(result: ReviewResult) -> str:
    by_kind = result.issues_by_kind
    art_map = result.articles_by_id
    lines = [f"\n{_THIN}", "  이슈 상세 목록", _THIN]

    for kind in IssueKind:
        items = by_kind.get(kind, [])
        if not items:
            continue
        label = ISSUE_LABEL[kind]
        lines.append(f"\n  ▸ {label} ({kind.value})  {len(items)}건")
        for issue in items:
            a = art_map.get(issue.article_id)
            if a:
                t = _fmt_time(a.published_at or a.collected_at)
                lines.append(f"    id={a.id:>6}  {a.title[:50]}  ({a.source_name}, {t})")
            else:
                lines.append(f"    id={issue.article_id}")
            lines.append(f"             {issue.detail}")

    return "\n".join(lines)


def _render_footer(result: ReviewResult) -> str:
    issue_count = len(result.issues)
    issue_art_count = len(result.issue_article_ids)
    generated = _now_kst_str()
    return (
        f"\n{_THIN}\n"
        f"  이슈 있는 기사: {issue_art_count}건 / 전체: {len(result.articles)}건  │  "
        f"생성: {generated}\n"
        f"{_THIN}"
    )


# ---------------------------------------------------------------------------
# JSON 렌더러 내부 구현
# ---------------------------------------------------------------------------


def _article_to_dict(a: ReviewArticle, result: ReviewResult) -> dict:
    issue_map = _build_issue_map(result.issues)
    return {
        "id": a.id,
        "title": a.title,
        "url": a.url,
        "source_name": a.source_name,
        "article_type": a.article_type,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "collected_at": a.collected_at.isoformat(),
        "summary": a.summary,
        "title_hash": a.title_hash,
        "symbols": a.symbols,
        "issues": [{"kind": i.kind.value, "detail": i.detail} for i in issue_map.get(a.id, [])],
    }


def _issue_to_dict(issue: ArticleIssue) -> dict:
    return {
        "article_id": issue.article_id,
        "kind": issue.kind.value,
        "detail": issue.detail,
    }


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------


def _build_issue_map(issues: list[ArticleIssue]) -> dict[int, list[ArticleIssue]]:
    """article_id → 이슈 목록 맵 생성."""
    result: dict[int, list[ArticleIssue]] = {}
    for issue in issues:
        result.setdefault(issue.article_id, []).append(issue)
    return result


def _fmt_dt(dt: datetime) -> str:
    """UTC datetime을 KST(+9) 날짜·시간 문자열로 포맷."""
    from datetime import timedelta

    kst = dt.astimezone(timezone(timedelta(hours=9)))
    return kst.strftime("%Y-%m-%d %H:%M KST")


def _fmt_time(dt: datetime) -> str:
    """시:분 KST 문자열."""
    from datetime import timedelta

    kst = dt.astimezone(timezone(timedelta(hours=9)))
    return kst.strftime("%H:%M")


def _now_kst_str() -> str:
    from datetime import timedelta

    from app.utils.datetime_utils import now_utc

    kst = now_utc().astimezone(timezone(timedelta(hours=9)))
    return kst.strftime("%Y-%m-%d %H:%M KST")
