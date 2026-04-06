"""Publisher 인터페이스 및 결과 모델.

Publisher Protocol: 브리핑 전달 채널을 위한 공통 계약.
  구현체만 교체하면 Console → File → Telegram → Slack 전환 가능.

PublishResult: 전송 결과 단위.
  success / detail / error를 담아 dispatcher에서 일괄 집계.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.briefing.models import MorningBriefing

# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass
class PublishResult:
    """단일 채널의 전송 결과.

    Attributes:
        publisher: 채널 식별자 (예: "console", "file:text", "telegram")
        success: 전송 성공 여부
        detail: 성공 시 보조 정보 (파일 경로, 메시지 ID 등),
                실패 시 오류 원인 설명
        error: 예외 객체 (성공 시 None)
    """

    publisher: str
    success: bool
    detail: str = ""
    error: Exception | None = field(default=None, repr=False)

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        suffix = f" | {self.detail}" if self.detail else ""
        return f"[{status}] {self.publisher}{suffix}"


# ---------------------------------------------------------------------------
# Publisher Protocol
# ---------------------------------------------------------------------------


class Publisher(Protocol):
    """브리핑 전달 채널 인터페이스.

    단일 메서드 publish()를 구현하면 어떤 채널이든 주입 가능.
    구현체는 publish() 내부에서 예외를 잡아 PublishResult.error에 담고
    성공/실패를 명시해야 한다 — 예외를 밖으로 전파하지 않는다.
    """

    @property
    def publisher_name(self) -> str:
        """채널 식별자. 로깅 및 결과 추적용."""
        ...

    def publish(self, briefing: MorningBriefing) -> PublishResult:
        """브리핑을 해당 채널로 전달한다.

        Args:
            briefing: 전달할 MorningBriefing 객체

        Returns:
            PublishResult — 예외는 error 필드에 담아 반환 (raise 금지)
        """
        ...
