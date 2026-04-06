"""유틸리티 / 기타 모듈 단위 테스트.

커버 대상:
  app/sources/watchlist.py
  app/summarizers/base.py
  app/summarizers/mock_summarizer.py
  app/summarizers/prompts/templates.py
  app/taggers/keyword_tagger.py
  app/db/connection.py  (DatabaseConfig)
  app/services/briefing_service.py  (BriefingQuery, BriefingResult)
"""

from datetime import datetime, timezone

import pytest

from app.db.connection import DatabaseConfig
from app.db.repositories.briefing_repository import BriefingArticle
from app.services.briefing_service import BriefingQuery, BriefingResult
from app.sources.watchlist import DEFAULT_WATCHLIST, WatchedSymbol
from app.summarizers.base import SummaryRequest, SummaryResponse, _fallback_response
from app.summarizers.mock_summarizer import MockSummarizer
from app.summarizers.prompts.templates import build_prompt
from app.taggers.keyword_tagger import KeywordTagger

_NOW = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
_SINCE = datetime(2024, 5, 31, 21, 0, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# WatchedSymbol / DEFAULT_WATCHLIST
# ---------------------------------------------------------------------------


class TestWatchlist:
    def test_default_watchlist_비어있지_않음(self):
        assert len(DEFAULT_WATCHLIST) > 0

    def test_watched_symbol_구조(self):
        ws = DEFAULT_WATCHLIST[0]
        assert isinstance(ws, WatchedSymbol)
        assert isinstance(ws.symbol, str)
        assert isinstance(ws.keywords, tuple)

    def test_nvda_포함(self):
        assert "NVDA" in [ws.symbol for ws in DEFAULT_WATCHLIST]

    def test_watched_symbol_생성(self):
        ws = WatchedSymbol(symbol="TEST", keywords=("테스트", "test"))
        assert ws.symbol == "TEST" and "테스트" in ws.keywords


# ---------------------------------------------------------------------------
# SummaryRequest / SummaryResponse
# ---------------------------------------------------------------------------


class TestSummaryRequest:
    def test_기본_생성(self):
        req = SummaryRequest(title="테스트", body="내용", source_name="소스", article_type="market")
        assert req.title == "테스트" and req.language == "ko"

    def test_symbols_기본값_빈_리스트(self):
        req = SummaryRequest(title="t", body="b", source_name="s", article_type="general")
        assert req.symbols == []


class TestSummaryResponse:
    def _req(self):
        return SummaryRequest(title="t", body="b", source_name="s", article_type="market")

    def test_text_줄바꿈_연결(self):
        resp = SummaryResponse(lines=["첫째 줄", "둘째 줄"], provider="mock", request=self._req())
        assert resp.text == "첫째 줄\n둘째 줄"

    def test_단일_줄(self):
        resp = SummaryResponse(lines=["한 줄"], provider="mock", request=self._req())
        assert resp.text == "한 줄"

    def test_최대_3줄_초과_에러(self):
        with pytest.raises(ValueError):
            SummaryResponse(lines=["a", "b", "c", "d"], provider="mock", request=self._req())

    def test_정확히_3줄_허용(self):
        resp = SummaryResponse(lines=["a", "b", "c"], provider="mock", request=self._req())
        assert len(resp.lines) == 3


class TestFallbackResponse:
    def test_폴백_응답_생성(self):
        req = SummaryRequest(title="t" * 100, body="b", source_name="s", article_type="general")
        resp = _fallback_response(req, "mock")
        assert "fallback" in resp.provider
        assert len(resp.lines) == 1
        assert len(resp.lines[0]) <= 80


# ---------------------------------------------------------------------------
# MockSummarizer
# ---------------------------------------------------------------------------


class TestMockSummarizer:
    def _req(self, article_type, symbols=None):
        return SummaryRequest(
            title="테스트 기사 제목입니다",
            body="기사 본문 내용",
            source_name="연합뉴스",
            article_type=article_type,
            symbols=symbols or [],
        )

    def test_provider_name(self):
        assert MockSummarizer().provider_name == "mock"

    def test_market_요약(self):
        resp = MockSummarizer().summarize(self._req("market"))
        assert 1 <= len(resp.lines) <= 3

    def test_company_요약(self):
        assert isinstance(MockSummarizer().summarize(self._req("company")).text, str)

    def test_company_요약_심볼포함(self):
        assert "NVDA" in MockSummarizer().summarize(self._req("company", symbols=["NVDA"])).text

    def test_event_요약(self):
        resp = MockSummarizer().summarize(self._req("event"))
        assert "예정" in resp.lines[0] or "이벤트" in resp.lines[0]

    def test_general_요약(self):
        assert len(MockSummarizer().summarize(self._req("general")).lines) >= 1

    def test_알수없는_타입_general_폴백(self):
        assert len(MockSummarizer().summarize(self._req("unknown_type")).lines) >= 1

    def test_긴_제목_잘림(self):
        req = SummaryRequest(
            title="가" * 100, body="내용", source_name="소스", article_type="market"
        )
        assert "..." in MockSummarizer().summarize(req).lines[0]

    def test_summarize_batch(self):
        reqs = [self._req(t) for t in ["market", "company", "event"]]
        assert len(MockSummarizer().summarize_batch(reqs)) == 3

    def test_summarize_batch_빈_목록(self):
        assert MockSummarizer().summarize_batch([]) == []


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def _req(self, article_type, symbols=None):
        return SummaryRequest(
            title="테스트 기사 제목",
            body="기사 내용",
            source_name="연합뉴스",
            article_type=article_type,
            symbols=symbols or [],
        )

    def test_market_프롬프트(self):
        prompt = build_prompt(self._req("market"))
        assert len(prompt) > 10

    def test_company_심볼_포함(self):
        assert "NVDA" in build_prompt(self._req("company", symbols=["NVDA"]))

    def test_event_프롬프트(self):
        assert isinstance(build_prompt(self._req("event")), str)

    def test_general_프롬프트(self):
        assert isinstance(build_prompt(self._req("general")), str)

    def test_unknown_타입_general_폴백(self):
        assert isinstance(build_prompt(self._req("unknown")), str)

    def test_프롬프트에_제목_포함(self):
        req = self._req("market")
        assert req.title in build_prompt(req)

    def test_내용없을때_내용없음_표시(self):
        req = SummaryRequest(title="제목", body="", source_name="소스", article_type="market")
        assert "(내용 없음)" in build_prompt(req)


# ---------------------------------------------------------------------------
# KeywordTagger
# ---------------------------------------------------------------------------


class TestKeywordTagger:
    @pytest.fixture
    def tagger(self):
        return KeywordTagger(watchlist=DEFAULT_WATCHLIST)

    def test_tagger_name(self, tagger):
        assert tagger.tagger_name == "keyword"

    def test_nvidia_매칭(self, tagger):
        assert "NVDA" in tagger.tag("엔비디아 주가 급등", "")

    def test_대소문자_무시(self, tagger):
        assert "NVDA" in tagger.tag("NVIDIA announced", "")

    def test_요약에서_매칭(self, tagger):
        assert "AAPL" in tagger.tag("오늘의 뉴스", "apple 아이폰 신제품 출시")

    def test_매칭_없으면_빈_리스트(self, tagger):
        assert tagger.tag("전혀 관계없는 기사", "내용도 관계없음") == []

    def test_여러_종목_매칭(self, tagger):
        result = tagger.tag("삼성전자 갤럭시 애플 아이폰", "")
        assert "005930" in result and "AAPL" in result

    def test_빈_watchlist(self):
        assert KeywordTagger(watchlist=[]).tag("엔비디아 주가", "") == []


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------


class TestDatabaseConfig:
    def test_직접_생성(self):
        config = DatabaseConfig(
            host="localhost", port=5432, dbname="mydb", user="user", password="pass"
        )
        assert config.host == "localhost" and config.port == 5432

    def test_from_env_기본값(self, monkeypatch):
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        monkeypatch.delenv("DB_NAME", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        config = DatabaseConfig.from_env()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.dbname == "news_collector"
        assert config.password == ""

    def test_from_env_환경변수_반영(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "myserver")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "testdb")
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "secret")
        config = DatabaseConfig.from_env()
        assert config.host == "myserver"
        assert config.port == 5433
        assert config.user == "testuser"


# ---------------------------------------------------------------------------
# BriefingQuery / BriefingResult
# ---------------------------------------------------------------------------


def _make_briefing_article(article_id, article_type="market"):
    return BriefingArticle(
        id=article_id,
        title=f"기사 {article_id}",
        url=f"https://example.com/{article_id}",
        source_name="소스",
        summary="요약",
        article_type=article_type,
        published_at=_NOW,
        collected_at=_NOW,
        symbols=[],
        ai_summary="",
    )


class TestBriefingQuery:
    def test_기본_생성(self):
        q = BriefingQuery(since=_SINCE, until=_UNTIL)
        assert q.since == _SINCE and q.until == _UNTIL and q.symbols == []

    def test_기본_limit_값(self):
        q = BriefingQuery(since=_SINCE, until=_UNTIL)
        assert q.market_limit == 20 and q.symbol_limit == 30 and q.event_limit == 10

    def test_symbols_지정(self):
        q = BriefingQuery(since=_SINCE, until=_UNTIL, symbols=["NVDA", "AAPL"])
        assert q.symbols == ["NVDA", "AAPL"]


class TestBriefingResult:
    def _make(self, market=None, symbol=None, event=None):
        return BriefingResult(
            query=BriefingQuery(since=_SINCE, until=_UNTIL),
            market_news=market or [],
            symbol_news=symbol or [],
            event_news=event or [],
        )

    def test_deduplicated_symbol_news_중복제거(self):
        a1 = _make_briefing_article(1)
        a2 = _make_briefing_article(2)
        dedup = self._make(market=[a1], symbol=[a1, a2]).deduplicated_symbol_news
        assert len(dedup) == 1 and dedup[0].id == 2

    def test_deduplicated_symbol_news_중복없으면_그대로(self):
        a1 = _make_briefing_article(1)
        a2 = _make_briefing_article(2)
        assert len(self._make(market=[a1], symbol=[a2]).deduplicated_symbol_news) == 1

    def test_log_summary_실행(self):
        result = self._make(
            market=[_make_briefing_article(1)],
            symbol=[_make_briefing_article(2)],
            event=[_make_briefing_article(3, article_type="event")],
        )
        result.log_summary()

    def test_to_dict_구조(self):
        d = self._make(market=[_make_briefing_article(1)]).to_dict()
        assert "since" in d and "market_news" in d and len(d["market_news"]) == 1
