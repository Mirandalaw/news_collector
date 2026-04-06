"""콘솔(stdout) Publisher.

브리핑을 표준 출력으로 인쇄한다.
개발 환경, 로컬 테스트, cron 로그 확인 용도.
"""

import logging

from app.briefing.models import MorningBriefing
from app.publishers.base import PublishResult

logger = logging.getLogger(__name__)


class ConsolePublisher:
    """브리핑을 stdout으로 출력하는 Publisher."""

    @property
    def publisher_name(self) -> str:
        return "console"

    def publish(self, briefing: MorningBriefing) -> PublishResult:
        try:
            print(briefing.to_text())
            return PublishResult(
                publisher=self.publisher_name,
                success=True,
                detail="stdout",
            )
        except Exception as e:
            logger.exception("콘솔 출력 실패")
            return PublishResult(
                publisher=self.publisher_name,
                success=False,
                detail="stdout 쓰기 실패",
                error=e,
            )
