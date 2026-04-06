"""투자 판단 보조 시그널 모델.

뉴스 해석 결과를 담는 불변 데이터 구조.

계층:
  Direction     : 방향성 (상승/하락/중립/혼재)
  Horizon       : 시간축 (단타 1~5일 / 장기 수주~수개월 / 공통)
  Importance    : 중요도 (HIGH / MEDIUM / LOW)
  Signal        : 단일 뉴스로부터 파생된 투자 판단 힌트
  SignalReport  : 전체 브리핑 분석 결과
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ---------------------------------------------------------------------------
# 열거형
# ---------------------------------------------------------------------------


class Direction(str, Enum):
    """시그널 방향성.

    BULLISH : 매수/보유 관점에서 긍정적
    BEARISH : 매수/보유 관점에서 부정적
    NEUTRAL : 방향성 불명확 (관망 또는 참고)
    MIXED   : 단기·장기 방향이 상반되거나 양면성이 있는 경우
    """

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


# 한국어 레이블
DIRECTION_LABEL: dict[Direction, str] = {
    Direction.BULLISH: "긍정 (Bullish)",
    Direction.BEARISH: "부정 (Bearish)",
    Direction.NEUTRAL: "중립 (Neutral)",
    Direction.MIXED: "혼재 (Mixed)",
}

# 콘솔 출력용 심볼
DIRECTION_ICON: dict[Direction, str] = {
    Direction.BULLISH: "▲",
    Direction.BEARISH: "▼",
    Direction.NEUTRAL: "─",
    Direction.MIXED: "±",
}


class Horizon(str, Enum):
    """투자 시간 지평선.

    SHORT : 단타/단기 (1~5 거래일 내 영향 예상)
    LONG  : 장기 (수주~수개월 영향 예상)
    BOTH  : 단·장기 모두 영향
    """

    SHORT = "short"
    LONG = "long"
    BOTH = "both"


HORIZON_LABEL: dict[Horizon, str] = {
    Horizon.SHORT: "단기",
    Horizon.LONG: "장기",
    Horizon.BOTH: "단·장기",
}


class Importance(str, Enum):
    """시그널 중요도.

    HIGH   : 시장 방향을 바꿀 수 있는 매크로/이벤트 (Fed, 실적 쇼크 등)
    MEDIUM : 섹터/종목 수준의 유의미한 변화
    LOW    : 배경 정보 수준. 단독으로 판단 근거 삼기 어려움.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


IMPORTANCE_LABEL: dict[Importance, str] = {
    Importance.HIGH: "★★★ 높음",
    Importance.MEDIUM: "★★☆ 중간",
    Importance.LOW: "★☆☆ 낮음",
}


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """단일 기사로부터 파생된 투자 판단 힌트.

    Attributes:
        article_id:    원본 기사 DB id
        article_title: 원본 기사 제목 (참조용)
        rule_name:     이 시그널을 생성한 규칙 이름
        direction:     방향성
        horizon:       시간 지평선
        importance:    중요도
        reason:        판단 근거 (사람이 읽는 설명)
        action_hint:   행동 힌트 (예: "포지션 축소 검토" — 자동 실행 아님)
        symbols:       영향 받는 종목 코드. 빈 리스트 = 시장 전체 영향
        source_name:   뉴스 소스
        published_at:  기사 발행 시각
    """

    article_id: int
    article_title: str
    rule_name: str
    direction: Direction
    horizon: Horizon
    importance: Importance
    reason: str
    action_hint: str
    symbols: list[str]
    source_name: str
    published_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "article_id": self.article_id,
            "article_title": self.article_title,
            "rule_name": self.rule_name,
            "direction": self.direction.value,
            "horizon": self.horizon.value,
            "importance": self.importance.value,
            "reason": self.reason,
            "action_hint": self.action_hint,
            "symbols": self.symbols,
            "source_name": self.source_name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


# ---------------------------------------------------------------------------
# SignalReport
# ---------------------------------------------------------------------------


@dataclass
class SignalReport:
    """브리핑 전체 분석 결과.

    Attributes:
        analyzed_at:     분석 시각 (UTC)
        briefing_since:  분석 대상 브리핑 시작 시각
        briefing_until:  분석 대상 브리핑 종료 시각
        signals:         감지된 시그널 전체 목록
        analyzed_count:  분석한 기사 수 (시그널 미발생 포함)
    """

    analyzed_at: datetime
    briefing_since: datetime
    briefing_until: datetime
    signals: list[Signal] = field(default_factory=list)
    analyzed_count: int = 0

    # ------------------------------------------------------------------
    # 파생 뷰
    # ------------------------------------------------------------------

    @property
    def high_signals(self) -> list[Signal]:
        return [s for s in self.signals if s.importance == Importance.HIGH]

    @property
    def by_horizon(self) -> dict[Horizon, list[Signal]]:
        result: dict[Horizon, list[Signal]] = defaultdict(list)
        for s in self.signals:
            if s.horizon in (Horizon.SHORT, Horizon.BOTH):
                result[Horizon.SHORT].append(s)
            if s.horizon in (Horizon.LONG, Horizon.BOTH):
                result[Horizon.LONG].append(s)
        return dict(result)

    @property
    def by_symbol(self) -> dict[str, list[Signal]]:
        result: dict[str, list[Signal]] = defaultdict(list)
        for s in self.signals:
            for sym in s.symbols:
                result[sym].append(s)
        return dict(result)

    @property
    def market_signals(self) -> list[Signal]:
        """종목 무관 시장 전체 시그널."""
        return [s for s in self.signals if not s.symbols]

    @property
    def direction_summary(self) -> dict[Direction, int]:
        counts: dict[Direction, int] = defaultdict(int)
        for s in self.signals:
            counts[s.direction] += 1
        return dict(counts)
