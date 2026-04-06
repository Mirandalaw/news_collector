"""아침 브리핑 생성 서비스.

외부 진입점: MorningBriefingService.generate(query) → MorningBriefing

파이프라인:
  BriefingQuery
    → BriefingService.run()    : DB 조회 + AI 요약 적용
    → build_morning_briefing() : 표시 모델로 변환
    → MorningBriefing          : to_text() / to_dict() 제공
"""

import logging

from app.briefing.builder import build_morning_briefing
from app.briefing.models import MorningBriefing
from app.db.connection import DatabaseConfig
from app.services.briefing_service import BriefingQuery, BriefingService
from app.summarizers.base import Summarizer

logger = logging.getLogger(__name__)


class MorningBriefingService:
    """아침 브리핑 생성 파이프라인.

    BriefingService(DB 조회 + 요약)를 내부에서 구동하고
    결과를 출력 가능한 MorningBriefing으로 변환한다.

    Args:
        db_config: PostgreSQL 접속 설정
        summarizer: LLM 요약기. None이면 원본 summary를 그대로 사용.
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        summarizer: Summarizer | None = None,
    ) -> None:
        self._briefing_service = BriefingService(db_config, summarizer)

    def generate(self, query: BriefingQuery) -> MorningBriefing:
        """브리핑을 생성한다.

        Args:
            query: 조회 파라미터 (시간 범위, 관심 종목, 섹션별 limit)

        Returns:
            MorningBriefing — to_text() / to_dict() 로 소비 가능

        Raises:
            psycopg2.OperationalError: DB 접속 실패 시
        """
        result = self._briefing_service.run(query)
        briefing = build_morning_briefing(result)

        logger.info(
            "브리핑 생성 완료 | since=%s | market=%d / symbol=%d / event=%d",
            query.since.strftime("%Y-%m-%d %H:%M UTC"),
            briefing.market_section.count,
            briefing.symbol_section.count,
            briefing.event_section.count,
        )
        return briefing
