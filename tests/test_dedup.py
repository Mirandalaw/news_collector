"""app/services/dedup.py + app/utils/hashing.py 단위 테스트.

DuplicateFilter 구현체의 계약과 hashing 유틸의 불변 조건을 검증한다.
"""

import pytest

from app.services.dedup import NullDuplicateFilter, TitleHashFilter
from app.utils.hashing import compute_title_hash, normalize_title


# ---------------------------------------------------------------------------
# hashing 유틸
# ---------------------------------------------------------------------------


class TestNormalizeTitle:
    def test_소문자_변환(self):
        assert normalize_title("HELLO WORLD") == "hello world"

    def test_대소문자_혼합(self):
        assert normalize_title("Apple MARKET") == "apple market"

    def test_연속_공백_정규화(self):
        assert normalize_title("a  b   c") == "a b c"

    def test_앞뒤_공백_제거(self):
        assert normalize_title("  hello  ") == "hello"

    def test_빈문자열(self):
        assert normalize_title("") == ""

    def test_줄바꿈_탭_처리(self):
        assert normalize_title("a\nb\tc") == "a b c"


class TestComputeTitleHash:
    def test_64자_hex_반환(self):
        result = compute_title_hash("타이틀")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_동일_입력_동일_해시(self):
        assert compute_title_hash("same title") == compute_title_hash("same title")

    def test_다른_입력_다른_해시(self):
        assert compute_title_hash("title a") != compute_title_hash("title b")

    def test_공백_차이_무시(self):
        """정규화로 인해 공백 차이는 같은 해시를 만든다."""
        assert compute_title_hash("금리 동결") == compute_title_hash("  금리  동결  ")

    def test_대소문자_차이_무시(self):
        assert compute_title_hash("Fed Rate Cut") == compute_title_hash("fed rate cut")

    def test_빈문자열_일관된_해시(self):
        h = compute_title_hash("")
        assert h == compute_title_hash("")
        assert len(h) == 64


# ---------------------------------------------------------------------------
# NullDuplicateFilter
# ---------------------------------------------------------------------------


class TestNullDuplicateFilter:
    def test_항상_false_반환(self, make_article):
        f = NullDuplicateFilter()
        a = make_article()
        assert f.is_duplicate(a) is False

    def test_mark_seen_후에도_false(self, make_article):
        """Null 필터는 상태를 유지하지 않는다."""
        f = NullDuplicateFilter()
        a = make_article()
        f.mark_seen(a)
        assert f.is_duplicate(a) is False

    def test_여러_기사_모두_false(self, make_article):
        f = NullDuplicateFilter()
        articles = [
            make_article(title=f"타이틀{i}", url=f"https://example.com/{i}") for i in range(5)
        ]
        for a in articles:
            assert f.is_duplicate(a) is False


# ---------------------------------------------------------------------------
# TitleHashFilter
# ---------------------------------------------------------------------------


class TestTitleHashFilter:
    def test_처음_기사는_중복_아님(self, make_article):
        f = TitleHashFilter()
        a = make_article()
        assert f.is_duplicate(a) is False

    def test_mark_seen_후_동일_해시_중복(self, make_article):
        f = TitleHashFilter()
        a = make_article(title="경제 기사")
        f.mark_seen(a)
        assert f.is_duplicate(a) is True

    def test_같은_타이틀_다른_url_중복(self, make_article):
        """URL이 달라도 타이틀이 같으면 중복."""
        f = TitleHashFilter()
        a1 = make_article(title="금리 동결", url="https://a.com/1")
        a2 = make_article(title="금리 동결", url="https://b.com/2")
        f.mark_seen(a1)
        assert f.is_duplicate(a2) is True

    def test_공백_차이_동일_타이틀_중복(self, make_article):
        """정규화 후 같은 타이틀이면 중복으로 처리."""
        f = TitleHashFilter()
        a1 = make_article(title="금리 동결", url="https://a.com/1")
        a2 = make_article(title="  금리  동결  ", url="https://b.com/2")
        f.mark_seen(a1)
        assert f.is_duplicate(a2) is True

    def test_다른_타이틀은_중복_아님(self, make_article):
        f = TitleHashFilter()
        a1 = make_article(title="기사 A", url="https://a.com/1")
        a2 = make_article(title="기사 B", url="https://a.com/2")
        f.mark_seen(a1)
        assert f.is_duplicate(a2) is False

    def test_빈_해시는_중복_처리_안함(self, make_article):
        """title_hash가 빈 문자열이면 필터를 우회한다."""
        f = TitleHashFilter()
        a1 = make_article(title="타이틀", title_hash="")
        a2 = make_article(title="타이틀", url="https://b.com/1", title_hash="")
        f.mark_seen(a1)
        assert f.is_duplicate(a2) is False  # hash 없으면 중복 판단 불가

    def test_필터_인스턴스_독립(self, make_article):
        """서로 다른 인스턴스는 상태를 공유하지 않는다."""
        f1 = TitleHashFilter()
        f2 = TitleHashFilter()
        a = make_article()
        f1.mark_seen(a)
        assert f2.is_duplicate(a) is False

    def test_순서대로_첫번째만_통과(self, make_article):
        """같은 타이틀 여러 건 중 첫 번째만 mark_seen 되어야 한다."""
        f = TitleHashFilter()
        articles = [
            make_article(title="동일 타이틀", url=f"https://example.com/{i}") for i in range(3)
        ]
        passed = []
        for a in articles:
            if not f.is_duplicate(a):
                f.mark_seen(a)
                passed.append(a)
        assert len(passed) == 1
        assert passed[0].url == "https://example.com/0"
