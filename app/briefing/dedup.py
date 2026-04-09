"""dedup v2 — 제목 기반 유사 기사 그룹핑 모듈.

구현 단계:
  STEP 1 (완료): normalize_title — 비교용 제목 정규화
  STEP 2 (완료): jaccard_similarity — 유사도 계산
  STEP 3-A (현재): group_by_similarity — 그룹핑 보조 함수
  STEP 3-B (예정): builder 적용
  STEP 4 (예정): 대표 기사 선택 고도화

이 모듈의 함수는 브리핑 표시용이 아니라 비교 전처리용이다.
원본 title을 변경하거나 DB에 저장하지 않는다.
"""

from __future__ import annotations

import re

from app.db.repositories.briefing_repository import BriefingArticle

# ---------------------------------------------------------------------------
# 정규화 패턴
# ---------------------------------------------------------------------------

# [속보], 【단독】, 〔긴급〕 등 괄호형 편집 태그
_RE_BRACKET_TAG = re.compile(r"\[.*?\]|【.*?】|〔.*?〕")

# 알파벳·한글·숫자·공백 외 특수문자 (마침표, 쉼표, 따옴표 등)
_RE_SPECIAL = re.compile(r"[^\w\s]", re.UNICODE)

# 중복 공백
_RE_SPACES = re.compile(r"\s+")

# 순수 편집 레이블 — 의미 없는 단어만 포함
# "전망", "오늘의" 등 내용에 영향을 줄 수 있는 단어는 제외
_NOISE_TOKENS: frozenset[str] = frozenset(["속보", "단독", "종합", "긴급", "특보", "업데이트"])

# ---------------------------------------------------------------------------
# 그룹핑 설정
# ---------------------------------------------------------------------------

SIMILARITY_THRESHOLD = 0.6  # 이 값 이상이면 동일 그룹으로 판단


# ---------------------------------------------------------------------------
# 공개 함수
# ---------------------------------------------------------------------------


def normalize_title(title: str) -> str:
    """비교용 제목 정규화.

    similarity 계산 전 두 제목을 동일한 형태로 만들기 위한 전처리 함수.
    원본 title 값을 변경하지 않는다.

    처리 순서:
      1. 소문자 변환
      2. 괄호형 편집 태그 제거 ([속보], 【단독】 등)
      3. 특수문자 제거 (알파벳·한글·숫자·공백만 유지)
      4. 노이즈 토큰 제거 (속보, 단독, 종합, 긴급, 특보, 업데이트)
      5. 공백 정규화

    Args:
        title: 원본 기사 제목

    Returns:
        정규화된 제목 문자열
    """
    text = title.lower()
    text = _RE_BRACKET_TAG.sub(" ", text)
    text = _RE_SPECIAL.sub(" ", text)

    tokens = [t for t in text.split() if t not in _NOISE_TOKENS]
    text = " ".join(tokens)

    return _RE_SPACES.sub(" ", text).strip()


def jaccard_similarity(a: str, b: str) -> float:
    """두 제목 간 단어 집합 기반 Jaccard similarity를 반환한다.

    내부적으로 normalize_title을 적용한 뒤 단어 set을 비교한다.
    빈 문자열이나 정규화 후 단어가 없는 경우 0.0을 반환한다.

    Args:
        a: 기사 제목 A
        b: 기사 제목 B

    Returns:
        0.0 ~ 1.0 범위의 유사도. 완전 동일하면 1.0, 공통 단어 없으면 0.0.
    """
    words_a = set(normalize_title(a).split())
    words_b = set(normalize_title(b).split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def group_by_similarity(
    articles: list[BriefingArticle],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[list[BriefingArticle]]:
    """유사한 기사들을 그룹으로 묶어 반환한다.

    그리디 방식으로 각 기사를 기존 그룹의 대표 기사(index 0)와 비교한다.
    similarity >= threshold이면 해당 그룹에 추가하고, 없으면 새 그룹을 생성한다.

    아래 조건에서는 similarity와 무관하게 그룹핑을 거부한다:
      - 두 기사의 symbols가 모두 비어 있지 않고 서로 다른 경우

    Args:
        articles: 그룹핑 대상 기사 리스트
        threshold: 동일 그룹 판단 기준 similarity (기본 0.6)

    Returns:
        그룹 리스트. 각 그룹은 1개 이상의 BriefingArticle로 구성된다.
        입력 순서 기준으로 첫 번째 기사가 각 그룹의 대표.
    """
    groups: list[list[BriefingArticle]] = []

    for article in articles:
        placed = False
        for group in groups:
            representative = group[0]
            if not _symbols_compatible(representative, article):
                continue
            if jaccard_similarity(representative.title, article.title) >= threshold:
                group.append(article)
                placed = True
                break
        if not placed:
            groups.append([article])

    return groups


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _symbols_compatible(a: BriefingArticle, b: BriefingArticle) -> bool:
    """두 기사를 같은 그룹으로 묶을 수 있는지 symbols 조건으로 판단한다.

    - 두 기사 모두 symbols가 비어 있으면 호환 (시장 기사끼리)
    - 두 기사의 symbols가 동일하면 호환
    - 한쪽만 symbols가 있거나 symbols가 서로 다르면 비호환
    """
    set_a = set(a.symbols)
    set_b = set(b.symbols)
    if not set_a and not set_b:
        return True
    return set_a == set_b
