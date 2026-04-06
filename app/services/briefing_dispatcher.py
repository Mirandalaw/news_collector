"""브리핑 생성 + 전송 오케스트레이터.

BriefingDispatcher.dispatch(query) 한 번으로
  1. MorningBriefingService → 브리핑 생성
  2. 등록된 Publisher 목록 → 순서대로 전달
  3. DispatchResult → 채널별 결과 집계

설계 원칙:
  - 개별 채널 실패가 다른 채널 전송을 막지 않는다.
  - Publisher 예외는 dispatcher가 잡아 PublishResult.error에 담는다.
  - 브리핑 생성 실패(DB 오류 등)는 전파한다 — 조용히 삼키지 않는다.
"""

import logging
from dataclasses import dataclass, field

from app.briefing.models import MorningBriefing
from app.publishers.base import Publisher, PublishResult
from app.services.briefing_service import BriefingQuery
from app.services.morning_briefing_service import MorningBriefingService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------

@dataclass
class DispatchResult:
    """dispatch() 전체 결과.

    Attributes:
        briefing: 생성된 MorningBriefing
        publish_results: 채널별 PublishResult 목록 (등록 순서)
    """

    briefing: MorningBriefing
    publish_results: list[PublishResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        """모든 채널 전송이 성공했으면 True."""
        return all(r.success for r in self.publish_results)

    @property
    def failed_results(self) -> list[PublishResult]:
        return [r for r in self.publish_results if not r.success]

    def log_summary(self) -> None:
        """채널별 결과를 로그로 요약한다."""
        total = len(self.publish_results)
        ok    = sum(1 for r in self.publish_results if r.success)
        logger.info("전송 결과 | %d/%d 채널 성공", ok, total)
        for result in self.publish_results:
            level = logging.INFO if result.success else logging.WARNING
            logger.log(level, "  %s", result)


# ---------------------------------------------------------------------------
# 디스패처
# ---------------------------------------------------------------------------

class BriefingDispatcher:
    """브리핑 생성 + 다중 채널 전달 파이프라인.

    Args:
        service: MorningBriefingService (브리핑 생성 담당)
        publishers: 전달 채널 목록. 등록 순서대로 순차 전송.
    """

    def __init__(
        self,
        service: MorningBriefingService,
        publishers: list[Publisher],
    ) -> None:
        if not publishers:
            raise ValueError("publishers는 최소 1개 이상이어야 합니다.")
        self._service    = service
        self._publishers = publishers

    def dispatch(self, query: BriefingQuery) -> DispatchResult:
        """브리핑을 생성하고 모든 채널로 전달한다.

        Args:
            query: 브리핑 조회 파라미터

        Returns:
            DispatchResult — 브리핑 객체 + 채널별 전송 결과

        Raises:
            psycopg2.OperationalError: 브리핑 생성 중 DB 오류 발생 시
        """
        briefing = self._service.generate(query)
        results  = self._publish_all(briefing)
        report   = DispatchResult(briefing=briefing, publish_results=results)
        report.log_summary()
        return report

    # ---------------------------------------------------------------------------
    # 내부 헬퍼
    # ---------------------------------------------------------------------------

    def _publish_all(self, briefing: MorningBriefing) -> list[PublishResult]:
        results: list[PublishResult] = []
        for publisher in self._publishers:
            result = self._safe_publish(publisher, briefing)
            results.append(result)
        return results

    def _safe_publish(
        self, publisher: Publisher, briefing: MorningBriefing
    ) -> PublishResult:
        """Publisher.publish()를 호출하고, 미처리 예외를 잡아 실패 결과로 변환한다."""
        try:
            return publisher.publish(briefing)
        except Exception as e:
            logger.exception(
                "Publisher 미처리 예외 | publisher=%s", publisher.publisher_name
            )
            return PublishResult(
                publisher=publisher.publisher_name,
                success=False,
                detail="미처리 예외 발생",
                error=e,
            )
