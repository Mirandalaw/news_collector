"""시그널 리포트 렌더러.

render_text()  → 콘솔/파일용 텍스트 출력
render_json()  → JSON 직렬화

출력 구조 (텍스트):
  1. 헤더 (분석 범위, 시그널 수, 방향성 요약)
  2. 핵심 시그널 (HIGH 중요도만)
  3. 단기 시그널 섹션
  4. 장기 시그널 섹션
  5. 종목별 시그널
  6. 면책 고지
"""

import json
from datetime import datetime, timedelta, timezone

from app.signals.models import (
    DIRECTION_ICON,
    DIRECTION_LABEL,
    HORIZON_LABEL,
    IMPORTANCE_LABEL,
    Horizon,
    Importance,
    Signal,
    SignalReport,
)

_W = 66
_THICK = "═" * _W
_THIN = "─" * _W
_KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def render_text(report: SignalReport) -> str:
    """SignalReport를 사람이 읽기 쉬운 텍스트로 렌더링한다."""
    parts: list[str] = []
    parts.append(_render_header(report))

    if not report.signals:
        parts.append("\n  이 브리핑에서 감지된 시그널이 없습니다.\n")
        parts.append(_DISCLAIMER)
        return "\n".join(parts)

    parts.append(_render_high_signals(report))
    parts.append(_render_horizon_section(report, Horizon.SHORT))
    parts.append(_render_horizon_section(report, Horizon.LONG))
    parts.append(_render_symbol_section(report))
    parts.append(_DISCLAIMER)
    return "\n".join(parts)


def render_json(report: SignalReport) -> str:
    """SignalReport를 JSON 문자열로 변환한다."""
    data = {
        "analyzed_at": _kst(report.analyzed_at),
        "briefing_since": report.briefing_since.isoformat(),
        "briefing_until": report.briefing_until.isoformat(),
        "analyzed_count": report.analyzed_count,
        "total_signals": len(report.signals),
        "direction_summary": {d.value: c for d, c in report.direction_summary.items()},
        "signals": [s.to_dict() for s in report.signals],
    }
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# 텍스트 렌더러 내부
# ---------------------------------------------------------------------------


def _render_header(report: SignalReport) -> str:
    since_str = _fmt_dt(report.briefing_since)
    until_str = _fmt_dt(report.briefing_until)
    dsummary = report.direction_summary

    direction_parts = "  ".join(
        f"{DIRECTION_ICON[d]}{d.value}:{c}"
        for d, c in sorted(dsummary.items(), key=lambda x: x[1], reverse=True)
        if c > 0
    )
    lines = [
        _THICK,
        f"  투자 시그널 리포트  │  {since_str} ~ {until_str}",
        f"  기사 {report.analyzed_count}건 분석  │  시그널 {len(report.signals)}건  │  {direction_parts}",
        _THICK,
    ]
    return "\n".join(lines)


def _render_high_signals(report: SignalReport) -> str:
    highs = [s for s in report.signals if s.importance == Importance.HIGH]
    if not highs:
        return ""

    lines = [f"\n  ★★★ 핵심 시그널 ({len(highs)}건) — 즉시 점검 권장", _THIN]
    for s in highs:
        lines.append(_render_signal_card(s, compact=True))
    return "\n".join(lines)


def _render_horizon_section(report: SignalReport, horizon: Horizon) -> str:
    by_h = report.by_horizon
    signals = by_h.get(horizon, [])
    if not signals:
        return ""

    label = HORIZON_LABEL[horizon]
    lines = [f"\n{_THIN}", f"  [{label} 시그널]  {len(signals)}건", _THIN]
    for s in signals:
        lines.append(_render_signal_card(s))
    return "\n".join(lines)


def _render_symbol_section(report: SignalReport) -> str:
    by_sym = report.by_symbol
    if not by_sym:
        return ""

    lines = [f"\n{_THIN}", "  [종목별 시그널]", _THIN]
    for symbol in sorted(by_sym.keys()):
        sym_signals = by_sym[symbol]
        lines.append(f"\n  ▸ {symbol}  ({len(sym_signals)}건)")
        for s in sym_signals:
            icon = DIRECTION_ICON[s.direction]
            imp = "★" * (
                3
                if s.importance == Importance.HIGH
                else 2
                if s.importance == Importance.MEDIUM
                else 1
            )
            lines.append(f"    {icon} [{imp}] [{HORIZON_LABEL[s.horizon]}] {s.rule_name}")
            lines.append(f"      근거: {s.reason[:70]}")
            if len(s.reason) > 70:
                lines.append(f"            {s.reason[70:]}")
            lines.append(f"      힌트: {s.action_hint[:70]}")
            lines.append(f"      출처: {s.source_name}")
            lines.append(f"      제목: {s.article_title[:60]}")
    return "\n".join(lines)


def _render_signal_card(s: Signal, compact: bool = False) -> str:
    icon = DIRECTION_ICON[s.direction]
    dir_l = DIRECTION_LABEL[s.direction]
    hor_l = HORIZON_LABEL[s.horizon]
    imp_l = IMPORTANCE_LABEL[s.importance]
    time_s = _fmt_time(s.published_at) if s.published_at else "??"
    sym_s = f"  [{', '.join(s.symbols)}]" if s.symbols else "  [시장전체]"

    lines = [
        f"\n  {icon} {dir_l}  │  {hor_l}  │  {imp_l}{sym_s}",
        f"     규칙: {s.rule_name}  ({s.source_name}, {time_s})",
        f"     근거: {s.reason}",
    ]
    if not compact:
        lines.append(f"     힌트: {s.action_hint}")
        lines.append(f"     기사: {s.article_title[:60]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 면책 고지
# ---------------------------------------------------------------------------

_DISCLAIMER = f"""
{_THIN}
  ⚠  주의사항 (반드시 읽으세요)
{_THIN}
  이 시그널은 뉴스 키워드 매칭 기반의 자동 해석 초안입니다.
  - 투자 판단의 최종 책임은 투자자 본인에게 있습니다.
  - 자동 매수/매도를 실행하지 마세요.
  - 하나의 시그널만으로 투자 결정을 내리지 마세요.
  - 시그널이 없다고 해서 안전하다는 의미가 아닙니다.
  - 키워드 오탐 가능성: 문맥 없는 매칭으로 방향이 틀릴 수 있습니다.
{_THIN}"""


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------


def _kst(dt: datetime) -> str:
    return dt.astimezone(_KST).strftime("%Y-%m-%d %H:%M KST")


def _fmt_dt(dt: datetime) -> str:
    return dt.astimezone(_KST).strftime("%Y-%m-%d %H:%M")


def _fmt_time(dt: datetime) -> str:
    return dt.astimezone(_KST).strftime("%H:%M")
