"""LLM 프롬프트 템플릿.

SummaryRequest → 프롬프트 문자열 변환 함수만 포함한다.
LLM 호출 코드 없음. 순수 함수이므로 단독 테스트 가능.

사용법:
  from app.summarizers.prompts.templates import build_prompt
  prompt = build_prompt(request)          # article_type에 맞는 프롬프트 선택
  response_text = llm_client.call(prompt) # 실제 LLM 호출은 구현체에서
"""

from app.summarizers.base import SummaryRequest


def build_prompt(request: SummaryRequest) -> str:
    """article_type에 따라 적합한 프롬프트를 선택해 반환한다.

    Args:
        request: 요약 요청

    Returns:
        LLM에 전달할 완성된 프롬프트 문자열
    """
    dispatch = {
        "market":  _market_prompt,
        "company": _company_prompt,
        "event":   _event_prompt,
    }
    builder = dispatch.get(request.article_type, _general_prompt)
    return builder(request)


# ---------------------------------------------------------------------------
# 섹션별 프롬프트 빌더 (순수 함수)
# ---------------------------------------------------------------------------

def _market_prompt(req: SummaryRequest) -> str:
    return f"""당신은 투자 전문가 어시스턴트입니다.
다음 시장/거시경제 뉴스를 아침 브리핑용으로 한국어 3줄 이내로 요약하세요.

작성 기준:
- 1줄: 핵심 사실 (구체적인 수치나 방향 포함)
- 2줄: 금융 시장(주식/채권/환율)에 대한 예상 영향
- 3줄: 투자자 관점의 주목 포인트 (선택)

제목: {req.title}
내용: {req.body or "(내용 없음)"}
출처: {req.source_name}

요약 (각 줄은 완성된 문장, "•" 없이):"""


def _company_prompt(req: SummaryRequest) -> str:
    symbol_context = (
        f"관련 종목: {', '.join(req.symbols)}\n" if req.symbols else ""
    )
    return f"""당신은 투자 전문가 어시스턴트입니다.
{symbol_context}다음 기업 뉴스를 아침 브리핑용으로 한국어 3줄 이내로 요약하세요.

작성 기준:
- 1줄: 기업이 무엇을 했는지 또는 어떤 이벤트가 발생했는지
- 2줄: 주가 또는 실적에 대한 예상 영향
- 3줄: 보유/관심 종목 투자자 관점 시사점 (선택)

제목: {req.title}
내용: {req.body or "(내용 없음)"}
출처: {req.source_name}

요약 (각 줄은 완성된 문장, "•" 없이):"""


def _event_prompt(req: SummaryRequest) -> str:
    return f"""당신은 투자 전문가 어시스턴트입니다.
다음 이벤트/발표 일정 뉴스를 아침 브리핑용으로 한국어 3줄 이내로 요약하세요.

작성 기준:
- 1줄: 언제, 어떤 이벤트가 예정되어 있는지
- 2줄: 해당 이벤트가 시장에 미칠 수 있는 영향
- 3줄: 사전 대비 또는 주목할 점 (선택)

제목: {req.title}
내용: {req.body or "(내용 없음)"}
출처: {req.source_name}

요약 (각 줄은 완성된 문장, "•" 없이):"""


def _general_prompt(req: SummaryRequest) -> str:
    return f"""당신은 투자 전문가 어시스턴트입니다.
다음 뉴스를 아침 브리핑용으로 한국어 2줄 이내로 간략히 요약하세요.

제목: {req.title}
내용: {req.body or "(내용 없음)"}
출처: {req.source_name}

요약 (각 줄은 완성된 문장, "•" 없이):"""
