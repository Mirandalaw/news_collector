"""LLM 요약 인터페이스 및 입출력 계약.

Summarizer Protocol: LLM 제공자와 무관한 요약 인터페이스.
  구현체만 교체하면 Mock → OpenAI → Claude 전환 가능.

사용 흐름:
  request = SummaryRequest(title=..., body=..., article_type="market")
  response = summarizer.summarize(request)
  print(response.text)
"""

import logging
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryRequest:
    """요약 요청 단위.

    Attributes:
        title: 기사 제목
        body: 기사 원문 요약 (RSS summary 필드. 없으면 빈 문자열)
        source_name: 뉴스 소스 (예: "연합뉴스")
        article_type: 의미 분류. 프롬프트 템플릿 선택에 사용.
                      "market" | "company" | "event" | "general"
        symbols: 관련 종목 코드. company 요약 시 컨텍스트로 활용.
        language: 출력 언어 힌트 (기본값 "ko")
    """

    title: str
    body: str
    source_name: str
    article_type: str
    symbols: list[str] = field(default_factory=list)
    language: str = "ko"


@dataclass(frozen=True)
class SummaryResponse:
    """요약 결과 단위.

    Attributes:
        lines: 요약 줄 목록. 최대 3개.
        provider: 요약을 생성한 구현체 이름 (예: "mock", "claude", "openai")
        request: 원본 요청 (역추적/디버깅용)
    """

    lines: list[str]
    provider: str
    request: SummaryRequest

    @property
    def text(self) -> str:
        """줄바꿈으로 연결된 단일 문자열."""
        return "\n".join(self.lines)

    def __post_init__(self) -> None:
        if len(self.lines) > 3:
            raise ValueError(f"SummaryResponse.lines는 최대 3개입니다. 현재: {len(self.lines)}")


class Summarizer(Protocol):
    """LLM 요약 인터페이스.

    단일 메서드 summarize()를 구현하면 어떤 LLM 제공자든 주입 가능.
    summarize_batch()는 기본 구현(순차 호출)을 제공하므로
    배치 API를 지원하는 구현체만 override하면 된다.
    """

    @property
    def provider_name(self) -> str:
        """구현체 식별자. 로깅 및 결과 추적용."""
        ...

    def summarize(self, request: SummaryRequest) -> SummaryResponse:
        """기사 1건을 요약한다.

        Args:
            request: 요약 요청 (제목, 본문, 타입, 종목 등)

        Returns:
            SummaryResponse (lines ≤ 3)
        """
        ...

    def summarize_batch(self, requests: list[SummaryRequest]) -> list[SummaryResponse]:
        """기사 목록을 일괄 요약한다.

        기본 구현은 summarize()를 순차 호출한다.
        API batch 엔드포인트를 지원하는 구현체는 이 메서드를 override해
        비용과 레이턴시를 최적화할 수 있다.
        """
        responses: list[SummaryResponse] = []
        for req in requests:
            try:
                responses.append(self.summarize(req))
            except Exception:
                logger.exception("요약 실패 - 건너뜀 | title=%.50s", req.title)
                responses.append(_fallback_response(req, self.provider_name))
        return responses


def _fallback_response(request: SummaryRequest, provider: str) -> SummaryResponse:
    """요약 실패 시 제목만 포함한 폴백 응답."""
    return SummaryResponse(
        lines=[request.title[:80]],
        provider=f"{provider}:fallback",
        request=request,
    )
