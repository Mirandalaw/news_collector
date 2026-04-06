"""시그널 규칙 기반 인터페이스 및 키워드 매칭 구현체.

SignalRule Protocol : 어떤 구현체든 주입 가능 (키워드, ML, LLM 등)
KeywordSignalRule  : 키워드 매칭 기반 구현체 — 규칙이 '데이터'로 표현됨

규칙이 데이터인 이유:
  - 직렬화/감사 가능 (어떤 규칙이 어떤 기사에 반응했는지 추적 가능)
  - 코드 변경 없이 규칙 추가/수정/비활성화 가능
  - 동일한 Protocol을 AI 기반 구현체로 교체 시 엔진 코드 불변
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.db.repositories.briefing_repository import BriefingArticle
from app.signals.models import Direction, Horizon, Importance, Signal

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SignalRule(Protocol):
    """시그널 규칙 인터페이스.

    evaluate() 하나만 구현하면 키워드 규칙, ML 모델, LLM 등 어떤 구현도 가능.
    None 반환 = 이 규칙은 해당 기사에 적용되지 않음.
    """

    @property
    def rule_name(self) -> str:
        """규칙 식별 이름. 시그널의 rule_name 필드에 기록된다."""
        ...

    def evaluate(self, article: BriefingArticle) -> Signal | None:
        """기사를 평가하고 시그널 또는 None을 반환한다.

        Args:
            article: 평가할 기사 (BriefingArticle DTO)

        Returns:
            Signal — 규칙이 발동된 경우
            None   — 규칙이 이 기사에 해당하지 않는 경우
        """
        ...


# ---------------------------------------------------------------------------
# KeywordSignalRule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeywordSignalRule:
    """키워드 substring 매칭 기반 시그널 규칙.

    Attributes:
        name:            규칙 식별 이름 (로그/감사용)
        trigger_keywords: 이 중 하나라도 title+summary에 포함되면 규칙 발동
        veto_keywords:   이 중 하나라도 포함되면 발동을 취소 (문맥 필터)
        direction:       발동 시 반환할 방향성
        horizon:         시간 지평선
        importance:      중요도
        reason:          판단 근거 설명 (브리핑에 그대로 표시됨)
        action_hint:     행동 힌트 — 자동 실행 아님, 참고용
        target_symbols:  이 종목에만 적용 (비어 있으면 전 종목/시장 적용)
        target_types:    이 article_type에만 적용 (비어 있으면 모든 타입)
        enabled:         False이면 엔진이 완전히 무시
    """

    name: str
    trigger_keywords: tuple[str, ...]
    direction: Direction
    horizon: Horizon
    importance: Importance
    reason: str
    action_hint: str
    veto_keywords: tuple[str, ...] = field(default_factory=tuple)
    target_symbols: tuple[str, ...] = field(default_factory=tuple)
    target_types: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True

    # Protocol 준수
    @property
    def rule_name(self) -> str:
        return self.name

    def evaluate(self, article: BriefingArticle) -> Signal | None:
        """기사에 규칙을 적용하고 시그널 또는 None을 반환한다."""
        if not self.enabled:
            return None

        # article_type 필터
        if self.target_types and article.article_type not in self.target_types:
            return None

        # 종목 필터 (target_symbols 지정 시 교집합이 있어야 함)
        if self.target_symbols:
            if not any(s in article.symbols for s in self.target_symbols):
                return None

        text = f"{article.title} {article.summary}".lower()

        # veto 먼저 체크 (있으면 발동 취소)
        if any(veto in text for veto in self.veto_keywords):
            return None

        # trigger 체크
        if not any(kw in text for kw in self.trigger_keywords):
            return None

        # 종목 컨텍스트: target_symbols 지정되면 그것만, 아니면 기사의 symbols
        symbols = (
            [s for s in article.symbols if s in self.target_symbols]
            if self.target_symbols
            else list(article.symbols)
        )

        return Signal(
            article_id=article.id,
            article_title=article.title,
            rule_name=self.name,
            direction=self.direction,
            horizon=self.horizon,
            importance=self.importance,
            reason=self.reason,
            action_hint=self.action_hint,
            symbols=symbols,
            source_name=article.source_name,
            published_at=article.published_at,
        )
