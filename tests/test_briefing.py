"""briefing 레이어 단위 테스트.

커버 대상:
  app/briefing/models.py
  app/briefing/builder.py
  app/briefing/renderer.py
  app/publishers/base.py
  app/publishers/console.py
"""

from datetime import datetime, timezone

from app.briefing.builder import build_morning_briefing
from app.briefing.models import BriefingItem, BriefingSection, MorningBriefing
from app.briefing.renderer import render_text
from app.db.repositories.briefing_repository import BriefingArticle
from app.publishers.base import PublishResult
from app.publishers.console import ConsolePublisher
from app.services.briefing_service import BriefingQuery, BriefingResult

_NOW = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
_SINCE = datetime(2024, 5, 31, 21, 0, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


def _make_item(
    article_id=1,
    title="테스트 기사",
    source_name="연합뉴스",
    url="https://example.com/1",
    summary_text="요약 텍스트입니다.",
    symbols=None,
    published_at=None,
):
    return BriefingItem(
        article_id=article_id,
        title=title,
        source_name=source_name,
        url=url,
        summary_text=summary_text,
        symbols=symbols or [],
        published_at=published_at,
    )


def _make_briefing_article(
    article_id=1,
    title="테스트 기사",
    article_type="market",
    summary="요약",
    ai_summary="",
    symbols=None,
):
    return BriefingArticle(
        id=article_id,
        title=title,
        url=f"https://example.com/{article_id}",
        source_name="테스트소스",
        summary=summary,
        article_type=article_type,
        published_at=_NOW,
        collected_at=_NOW,
        symbols=symbols or [],
        ai_summary=ai_summary,
    )


def _make_briefing(market=None, symbol=None, event=None):
    query = BriefingQuery(since=_SINCE, until=_UNTIL)
    result = BriefingResult(
        query=query,
        market_news=market or [],
        symbol_news=symbol or [],
        event_news=event or [],
    )
    return build_morning_briefing(result)


class TestBriefingItem:
    def test_기본_생성(self):
        item = _make_item()
        assert item.title == "테스트 기사"
        assert item.symbols == []
        assert item.published_at is None

    def test_심볼_포함(self):
        item = _make_item(symbols=["NVDA", "AAPL"])
        assert item.symbols == ["NVDA", "AAPL"]

    def test_published_at_포함(self):
        item = _make_item(published_at=_NOW)
        assert item.published_at == _NOW


class TestBriefingSection:
    def test_빈_섹션_is_empty(self):
        section = BriefingSection(title="시장", emoji="📈", items=[])
        assert section.is_empty is True
        assert section.count == 0

    def test_아이템_있으면_is_empty_false(self):
        section = BriefingSection(title="시장", emoji="📈", items=[_make_item()])
        assert section.is_empty is False
        assert section.count == 1

    def test_to_dict_구조(self):
        items = [_make_item(article_id=i, url=f"https://example.com/{i}") for i in range(3)]
        section = BriefingSection(title="시장", emoji="📈", items=items)
        d = section.to_dict()
        assert d["title"] == "시장"
        assert d["count"] == 3
        assert len(d["items"]) == 3

    def test_to_dict_item_published_at_none(self):
        section = BriefingSection(title="시장", emoji="📈", items=[_make_item(published_at=None)])
        d = section.to_dict()
        assert d["items"][0]["published_at"] is None

    def test_to_dict_item_published_at_iso(self):
        section = BriefingSection(title="시장", emoji="📈", items=[_make_item(published_at=_NOW)])
        d = section.to_dict()
        assert d["items"][0]["published_at"] == _NOW.isoformat()


class TestMorningBriefing:
    def test_sections_3개(self):
        briefing = _make_briefing()
        assert len(briefing.sections) == 3

    def test_total_items_합산(self):
        briefing = _make_briefing(market=[_make_briefing_article()])
        assert briefing.total_items == 1

    def test_total_items_빈_브리핑(self):
        assert _make_briefing().total_items == 0

    def test_to_dict_구조(self):
        d = _make_briefing().to_dict()
        assert "generated_at" in d
        assert "sections" in d
        assert "market" in d["sections"]

    def test_to_text_문자열(self):
        text = _make_briefing().to_text()
        assert isinstance(text, str) and len(text) > 0


class TestBuildMorningBriefing:
    def test_market_섹션_변환(self):
        article = _make_briefing_article(title="시장 기사")
        briefing = _make_briefing(market=[article])
        assert briefing.market_section.count == 1

    def test_ai_summary_우선(self):
        article = _make_briefing_article(summary="원본요약", ai_summary="AI요약")
        briefing = _make_briefing(market=[article])
        assert briefing.market_section.items[0].summary_text == "AI요약"

    def test_ai_summary_없으면_원본_사용(self):
        article = _make_briefing_article(summary="원본요약", ai_summary="")
        briefing = _make_briefing(market=[article])
        assert briefing.market_section.items[0].summary_text == "원본요약"

    def test_symbol_섹션_dedup(self):
        a1 = _make_briefing_article(article_id=1)
        a2 = _make_briefing_article(article_id=2)
        briefing = _make_briefing(market=[a1], symbol=[a1, a2])
        assert briefing.symbol_section.count == 1
        assert briefing.symbol_section.items[0].article_id == 2

    def test_event_섹션_변환(self):
        article = _make_briefing_article(article_id=10, title="이벤트", article_type="event")
        briefing = _make_briefing(event=[article])
        assert briefing.event_section.count == 1


class TestRenderText:
    def test_헤더_포함(self):
        text = render_text(_make_briefing())
        assert "아침 브리핑" in text

    def test_빈_섹션_메시지(self):
        text = render_text(_make_briefing())
        assert "관련 뉴스가 없습니다." in text

    def test_아이템_제목_포함(self):
        article = _make_briefing_article(title="금리 인하 결정")
        text = render_text(_make_briefing(market=[article]))
        assert "금리 인하 결정" in text

    def test_심볼_태그_표시(self):
        item = _make_item(symbols=["NVDA"])
        section = BriefingSection(title="종목", emoji="🔍", items=[item])
        briefing = MorningBriefing(
            generated_at=_NOW,
            since=_SINCE,
            until=_UNTIL,
            market_section=BriefingSection(title="시장", emoji="📈"),
            symbol_section=section,
            event_section=BriefingSection(title="이벤트", emoji="📅"),
        )
        assert "NVDA" in render_text(briefing)

    def test_published_at_표시(self):
        item = _make_item(published_at=_NOW)
        section = BriefingSection(title="시장", emoji="📈", items=[item])
        briefing = MorningBriefing(
            generated_at=_NOW,
            since=_SINCE,
            until=_UNTIL,
            market_section=section,
            symbol_section=BriefingSection(title="종목", emoji="🔍"),
            event_section=BriefingSection(title="이벤트", emoji="📅"),
        )
        assert "06/01" in render_text(briefing)

    def test_요약_없으면_렌더링_가능(self):
        item = _make_item(summary_text="")
        section = BriefingSection(title="시장", emoji="📈", items=[item])
        briefing = MorningBriefing(
            generated_at=_NOW,
            since=_SINCE,
            until=_UNTIL,
            market_section=section,
            symbol_section=BriefingSection(title="종목", emoji="🔍"),
            event_section=BriefingSection(title="이벤트", emoji="📅"),
        )
        assert item.title in render_text(briefing)

    def test_멀티라인_요약(self):
        item = _make_item(summary_text="첫 번째 줄\n두 번째 줄")
        section = BriefingSection(title="시장", emoji="📈", items=[item])
        briefing = MorningBriefing(
            generated_at=_NOW,
            since=_SINCE,
            until=_UNTIL,
            market_section=section,
            symbol_section=BriefingSection(title="종목", emoji="🔍"),
            event_section=BriefingSection(title="이벤트", emoji="📅"),
        )
        text = render_text(briefing)
        assert "첫 번째 줄" in text
        assert "두 번째 줄" in text

    def test_푸터_포함(self):
        article = _make_briefing_article(title="시장 기사")
        text = render_text(_make_briefing(market=[article]))
        assert "오늘 시장" in text


class TestPublishResult:
    def test_성공_str(self):
        r = PublishResult(publisher="console", success=True, detail="stdout")
        assert "[OK]" in str(r) and "console" in str(r)

    def test_실패_str(self):
        assert "[FAIL]" in str(PublishResult(publisher="telegram", success=False))

    def test_detail_없으면_파이프_없음(self):
        assert "|" not in str(PublishResult(publisher="console", success=True))


class TestConsolePublisher:
    def test_publisher_name(self):
        assert ConsolePublisher().publisher_name == "console"

    def test_publish_성공(self, capsys):
        result = ConsolePublisher().publish(_make_briefing())
        assert result.success is True
        assert "아침 브리핑" in capsys.readouterr().out

    def test_publish_예외_처리(self, monkeypatch):
        """renderer가 예외를 던지면 PublishResult.success=False를 반환해야 한다."""
        # MorningBriefing은 frozen dataclass라 직접 monkeypatch 불가.
        # renderer 모듈 함수를 패치한다.
        import app.briefing.renderer as renderer_mod

        monkeypatch.setattr(
            renderer_mod, "render_text", lambda _: (_ for _ in ()).throw(RuntimeError("fail"))
        )
        result = ConsolePublisher().publish(_make_briefing())
        assert result.success is False
        assert result.error is not None
