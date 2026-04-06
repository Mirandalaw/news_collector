"""app/parsers/rss_parser.py 단위 테스트.

feedparser entry를 SimpleNamespace로 모킹해 네트워크 없이 파싱 로직을 검증한다.
"""

import time
from datetime import datetime, timezone

import pytest

from app.parsers.rss_parser import _normalize_whitespace, _strip_html, parse_entry
from tests.conftest import make_feed_entry

# ---------------------------------------------------------------------------
# parse_entry - 정상 케이스
# ---------------------------------------------------------------------------


class TestParseEntryNormal:
    def test_기본_필드_추출(self):
        entry = make_feed_entry(title="금리 동결 결정", link="https://news.com/1")
        result = parse_entry(entry, "테스트소스", "경제")
        assert result is not None
        assert result.title == "금리 동결 결정"
        assert result.url == "https://news.com/1"
        assert result.source_name == "테스트소스"
        assert result.category == "경제"

    def test_title_hash_자동_계산(self):
        entry = make_feed_entry(title="해시 테스트")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert len(result.title_hash) == 64  # SHA-256 hex digest

    def test_published_at_파싱(self):
        t = time.strptime("2024-06-01 09:00:00", "%Y-%m-%d %H:%M:%S")
        entry = make_feed_entry(published_parsed=t)
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.published_at == datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

    def test_published_at_없으면_none(self):
        entry = make_feed_entry(published_parsed=None)
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.published_at is None

    def test_collected_at_주입(self):
        fixed = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        entry = make_feed_entry()
        result = parse_entry(entry, "소스", "경제", collected_at=fixed)
        assert result is not None
        assert result.collected_at == fixed

    def test_collected_at_미주입시_utc_now(self):
        entry = make_feed_entry()
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.collected_at.tzinfo is timezone.utc

    def test_summary_없으면_빈문자열(self):
        entry = make_feed_entry(summary="", description="")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.summary == ""


# ---------------------------------------------------------------------------
# parse_entry - 필수 필드 누락 → None 반환
# ---------------------------------------------------------------------------


class TestParseEntryMissingFields:
    def test_title_없으면_none(self):
        entry = make_feed_entry(title="")
        assert parse_entry(entry, "소스", "경제") is None

    def test_title_공백만_있으면_none(self):
        entry = make_feed_entry(title="   ")
        assert parse_entry(entry, "소스", "경제") is None

    def test_url_없으면_none(self):
        entry = make_feed_entry(link="")
        assert parse_entry(entry, "소스", "경제") is None

    def test_title_none_타입이면_none(self):
        entry = make_feed_entry(title=None)
        assert parse_entry(entry, "소스", "경제") is None


# ---------------------------------------------------------------------------
# parse_entry - 데이터 정제
# ---------------------------------------------------------------------------


class TestParseEntryDataCleaning:
    def test_title_앞뒤_공백_제거(self):
        entry = make_feed_entry(title="  공백 타이틀  ")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.title == "공백 타이틀"

    def test_title_내부_공백_정규화(self):
        entry = make_feed_entry(title="공백이  많은  타이틀")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.title == "공백이 많은 타이틀"

    def test_summary_html_태그_제거(self):
        entry = make_feed_entry(summary="<p>기사 <b>내용</b>입니다</p>")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert "<" not in result.summary
        assert "기사" in result.summary
        assert "내용" in result.summary

    def test_summary_html_엔티티_변환(self):
        entry = make_feed_entry(summary="주가 &amp; 환율 &lt;급락&gt;")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert "&amp;" not in result.summary
        assert "&lt;" not in result.summary
        assert "주가 & 환율" in result.summary

    def test_summary_우선_description_폴백(self):
        entry = make_feed_entry(summary="summary 값", description="description 값")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.summary == "summary 값"

    def test_summary_없을때_description_사용(self):
        entry = make_feed_entry(summary="", description="description 폴백")
        result = parse_entry(entry, "소스", "경제")
        assert result is not None
        assert result.summary == "description 폴백"

    def test_title_hash는_정규화된_타이틀_기준(self):
        """공백 차이가 있어도 동일한 내용이면 같은 해시."""
        e1 = make_feed_entry(title="금리 동결", link="https://a.com/1")
        e2 = make_feed_entry(title="  금리  동결  ", link="https://b.com/1")
        r1 = parse_entry(e1, "소스", "경제")
        r2 = parse_entry(e2, "소스", "경제")
        assert r1 is not None and r2 is not None
        assert r1.title_hash == r2.title_hash


# ---------------------------------------------------------------------------
# 내부 헬퍼 직접 테스트
# ---------------------------------------------------------------------------


class TestStripHtml:
    def test_태그_제거(self):
        assert "hello" in _strip_html("<p>hello</p>")

    def test_중첩_태그(self):
        result = _strip_html("<div><p><b>내용</b></p></div>")
        assert "<" not in result
        assert "내용" in result

    def test_태그_없으면_원본_유지(self):
        assert _strip_html("plain text") == "plain text"

    @pytest.mark.parametrize(
        "entity,expected",
        [
            ("&amp;", "&"),
            ("&lt;", "<"),
            ("&gt;", ">"),
            ("&quot;", '"'),
            ("&#39;", "'"),
            ("&nbsp;", " "),
        ],
    )
    def test_html_엔티티_변환(self, entity, expected):
        assert _strip_html(entity) == expected


class TestNormalizeWhitespace:
    def test_연속_공백_단일화(self):
        assert _normalize_whitespace("a  b   c") == "a b c"

    def test_줄바꿈_공백으로(self):
        assert _normalize_whitespace("a\nb\tc") == "a b c"

    def test_앞뒤_공백_제거(self):
        assert _normalize_whitespace("  hello  ") == "hello"

    def test_빈문자열(self):
        assert _normalize_whitespace("") == ""
