"""타이틀 해시 생성 유틸리티.

정규화된 타이틀을 SHA-256으로 해싱한다.
같은 내용의 기사가 URL만 다르게 재배포될 때 중복을 감지하기 위한 용도.
"""

import hashlib
import re

_WHITESPACE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """타이틀을 소문자 + 공백 정규화한 형태로 반환한다.

    해시 계산 전 전처리로, 공백/대소문자 차이로 인한 해시 불일치를 방지한다.
    """
    return _WHITESPACE.sub(" ", title.lower()).strip()


def compute_title_hash(title: str) -> str:
    """정규화된 타이틀의 SHA-256 hex digest를 반환한다.

    Args:
        title: 원본 타이틀 문자열

    Returns:
        64자 hex 문자열 (SHA-256)
    """
    normalized = normalize_title(title)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
