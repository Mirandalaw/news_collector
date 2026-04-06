"""날짜/시간 변환 유틸리티.

feedparser가 반환하는 time.struct_time을 UTC datetime으로 변환한다.
"""

import calendar
import logging
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def parse_struct_time_to_utc(t: time.struct_time | None) -> datetime | None:
    """feedparser의 published_parsed(time.struct_time, UTC 기준)를 datetime으로 변환한다.

    feedparser는 published_parsed를 항상 UTC로 정규화해 반환한다.
    tzinfo를 명시적으로 UTC로 지정해 naive datetime을 방지한다.

    Args:
        t: feedparser entry.published_parsed 값. None이면 None을 반환한다.

    Returns:
        UTC timezone-aware datetime. 변환 실패 또는 None 입력 시 None.
    """
    if t is None:
        return None

    try:
        timestamp = calendar.timegm(t)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        logger.warning("published_parsed 변환 실패: %r", t)
        return None


def now_utc() -> datetime:
    """현재 시각을 UTC timezone-aware datetime으로 반환한다."""
    return datetime.now(timezone.utc)


def morning_briefing_window(
    as_of: datetime | None = None,
    hours_back: int = 12,
) -> tuple[datetime, datetime]:
    """아침 브리핑용 시간 범위(since, until)를 반환한다.

    Args:
        as_of: 기준 시각. None이면 현재 UTC 시각 사용.
        hours_back: 기준 시각으로부터 몇 시간 전까지 포함할지 (기본 12시간).
                    한국 기준 아침 9시 → 전날 밤 9시(21시) 이후 = 12시간.

    Returns:
        (since, until) tuple. 두 값 모두 UTC timezone-aware.

    Examples:
        since, until = morning_briefing_window()           # 최근 12시간
        since, until = morning_briefing_window(hours_back=16)  # 전날 장마감 이후
    """
    until = as_of or now_utc()
    since = until - timedelta(hours=hours_back)
    return since, until
