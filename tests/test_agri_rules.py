"""농산물 규칙·watchlist 동작 확인 (DB 불필요)."""
from datetime import datetime, timezone

from app.db.repositories.briefing_repository import BriefingArticle
from app.signals.models import Direction
from app.signals.rules.agri_rules import AGRI_RULES
from app.sources.agri_watchlist import AGRI_WATCHLIST
from app.taggers.keyword_tagger import KeywordTagger


def _art(title, summary="", symbols=()):
    return BriefingArticle(
        id=1, title=title, url="https://x", source_name="t", summary=summary,
        article_type="general", published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc), symbols=list(symbols),
    )


def _fire(title, symbols=()):
    return {r.name: s for r in AGRI_RULES if (s := r.evaluate(_art(title, symbols=symbols)))}


def test_tagger_maps_items():
    tagger = KeywordTagger(AGRI_WATCHLIST)
    assert tagger.tag("가을배추 출하 본격화…해남 산지 물량 증가", "") == ["배추"]
    assert set(tagger.tag("정부, 깐마늘·양파 TRQ 증량 결정", "")) == {"깐마늘", "양파"}
    assert tagger.tag("추석 맞이 음식 레시피 소개", "") == []


def test_reserve_release_is_bearish_short():
    s = _fire("정부, 가을배추 비축물량 1만톤 방출", symbols=("배추",))
    assert "agri_reserve_release" in s
    assert s["agri_reserve_release"].direction == Direction.BEARISH


def test_posthoc_article_is_vetoed():
    assert "agri_reserve_release" not in _fire("금배추에 비축 방출에도 포기당 2만원 껑충", symbols=("배추",))


def test_import_rule_only_for_imported_items():
    assert "agri_import_up" in _fire("깐마늘 TRQ 증량", symbols=("깐마늘",))
    assert "agri_import_up" not in _fire("배추 TRQ 증량", symbols=("배추",))


def test_typhoon_is_bullish_no_negation_flip():
    s = _fire("태풍 피해 우려에 산지 긴장", symbols=("무",))
    assert s["agri_typhoon"].direction == Direction.BULLISH


def test_reserve_buy_vs_release():
    buy = _fire("농식품부, 배추 2만톤 수매 확대·시장격리", symbols=("배추",))
    assert "agri_reserve_buy" in buy and "agri_reserve_release" not in buy
    rel = _fire("비축 배추 하루 200톤 방출", symbols=("배추",))
    assert "agri_reserve_release" in rel and "agri_reserve_buy" not in rel
