"""app/utils/datetime_utils.py 단위 테스트.

순수 함수 위주로, 경계값과 예외 경로를 검증한다.
"""

import time
from datetime import datetime, timezone

import pytest

from app.utils.datetime_utils import now_utc, parse_struct_time_to_utc


class TestParseStructTimeToUtc:
    def test_정상_변환(self):
        # 2024-01-15 10:30:00 UTC
        t = time.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
        result = parse_struct_time_to_utc(t)
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_none_입력은_none_반환(self):
        assert parse_struct_time_to_utc(None) is None

    def test_반환값은_utc_aware(self):
        t = time.gmtime()
        result = parse_struct_time_to_utc(t)
        assert result is not None
        assert result.tzinfo is timezone.utc

    def test_유닉스_에포크(self):
        # 1970-01-01 00:00:00 UTC
        t = time.gmtime(0)
        result = parse_struct_time_to_utc(t)
        assert result == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_말일_시각(self):
        t = time.strptime("2024-12-31 23:59:59", "%Y-%m-%d %H:%M:%S")
        result = parse_struct_time_to_utc(t)
        assert result == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    def test_feedparser_typical_struct(self):
        """feedparser가 실제로 반환하는 9-tuple 형태 검증."""
        # feedparser published_parsed 는 time.struct_time (9개 필드)
        t = time.struct_time((2024, 3, 20, 8, 0, 0, 2, 80, 0))
        result = parse_struct_time_to_utc(t)
        assert result == datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc)


class TestNowUtc:
    def test_utc_aware_반환(self):
        result = now_utc()
        assert result.tzinfo is timezone.utc

    def test_naive_아님(self):
        result = now_utc()
        assert result.utcoffset() is not None

    def test_호출마다_증가(self):
        t1 = now_utc()
        t2 = now_utc()
        assert t2 >= t1
