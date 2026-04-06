"""Mock 요약기.

외부 API 없이 브리핑 구조와 포맷을 검증하기 위한 placeholder 구현체.
제목을 기반으로 article_type별 고정 포맷의 가짜 요약을 생성한다.

사용 목적:
  - 개발/테스트 환경에서 LLM 비용 없이 전체 파이프라인 구동
  - 출력 포맷 확인 및 UI 프로토타이핑
  - CI/CD에서 실제 API 없이 통합 테스트 수행
"""

import logging

from app.summarizers.base import SummaryRequest, SummaryResponse

logger = logging.getLogger(__name__)


class MockSummarizer:
    """네트워크 없는 placeholder 요약기.

    실제 LLM 출력을 흉내낸 포맷으로 생성하되,
    제목의 앞 40자를 재활용해 기사별로 구분 가능하게 만든다.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        lines = self._build_lines(request)
        logger.debug("mock 요약 생성 | type=%s | title=%.40s", request.article_type, request.title)
        return SummaryResponse(lines=lines, provider=self.provider_name, request=request)

    def summarize_batch(self, requests: list[SummaryRequest]) -> list[SummaryResponse]:
        return [self.summarize(r) for r in requests]

    # ---------------------------------------------------------------------------
    # 내부 헬퍼
    # ---------------------------------------------------------------------------

    def _build_lines(self, req: SummaryRequest) -> list[str]:
        short_title = req.title[:45].rstrip()
        dispatch = {
            "market":  self._market_lines,
            "company": self._company_lines,
            "event":   self._event_lines,
        }
        builder = dispatch.get(req.article_type, self._general_lines)
        return builder(req, short_title)

    @staticmethod
    def _market_lines(req: SummaryRequest, title: str) -> list[str]:
        return [
            f"{title}{'...' if len(req.title) > 45 else ''} 관련 시장 동향이 확인됩니다.",
            "주요 지수 및 금리 변동 여부를 장중 모니터링하세요.",
            "거시 변수 변화에 따른 포트폴리오 영향 점검이 필요합니다.",
        ]

    @staticmethod
    def _company_lines(req: SummaryRequest, title: str) -> list[str]:
        sym_str = f" ({', '.join(req.symbols)})" if req.symbols else ""
        return [
            f"{title}{'...' if len(req.title) > 45 else ''}{sym_str} 관련 기업 뉴스입니다.",
            "해당 기업의 주가 및 실적 영향 여부를 확인하세요.",
            "보유 종목이라면 추가 공시 및 애널리스트 리포트를 참조하세요.",
        ]

    @staticmethod
    def _event_lines(req: SummaryRequest, title: str) -> list[str]:
        return [
            f"예정 이벤트: {title}{'...' if len(req.title) > 45 else ''}",
            "해당 발표 전후 변동성 확대에 대비하세요.",
            "이벤트 일정과 예상 컨센서스를 미리 확인하세요.",
        ]

    @staticmethod
    def _general_lines(req: SummaryRequest, title: str) -> list[str]:
        return [
            f"{title}{'...' if len(req.title) > 45 else ''} 관련 동향이 보고됩니다.",
            "추가 정보를 원문에서 확인하세요.",
        ]
