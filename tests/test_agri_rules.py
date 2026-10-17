"""농산물 규칙·watchlist 동작 확인 (DB 불필요)."""

from datetime import datetime, timezone

from app.db.repositories.briefing_repository import BriefingArticle
from app.signals.models import Direction
from app.signals.rules.agri_rules import AGRI_RULES
from app.sources.agri_watchlist import AGRI_WATCHLIST
from app.taggers.keyword_tagger import KeywordTagger


def _art(title, summary="", symbols=()):
    return BriefingArticle(
        id=1,
        title=title,
        url="https://x",
        source_name="t",
        summary=summary,
        article_type="general",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        symbols=list(symbols),
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


def test_posthoc_wording_no_longer_vetoes_policy_event():
    # 2021~2024 코퍼스: 정부 대책 기사 대부분이 제목에 '껑충·금배추'를 함께 쓴다
    # → 사건은 살리고 사후 보도는 플래그로만
    from app.signals.agri_features import is_posthoc

    title = "금배추에 비축 방출에도 포기당 2만원 껑충"
    assert "agri_reserve_release" in _fire(title, symbols=("배추",))
    assert is_posthoc(title) and not is_posthoc("농식품부, 배추 비축물량 3000톤 공급")


def test_non_event_context_still_vetoed():
    assert not _fire("김장철 앞두고 원산지 단속…배추 비축 방출 언급", symbols=("배추",))
    assert not _fire("[칼럼] 배추 비축 방출의 정치경제학", symbols=("배추",))


def test_import_rule_covers_cabbage_imports_too():
    assert "agri_import_up" in _fire("깐마늘 TRQ 증량", symbols=("깐마늘",))
    assert "agri_import_up" in _fire("정부, 중국산 배추 수입 추진", symbols=("배추",))


def test_release_rule_catches_supply_expansion_wording():
    assert "agri_reserve_release" in _fire(
        "배추·무 가격 폭등에 추석 농산물 4000톤 추가 공급", symbols=("배추", "무")
    )
    assert "agri_reserve_release" in _fire("가을배추 2200t 푼다…할인 지원", symbols=("배추",))


def test_mu_tagging_in_item_lists():
    from app.sources.agri_watchlist import AgriTagger

    t = AgriTagger()
    assert t.tag("배추·무·감자 가격 폭등에 추석 농산물 4000톤 추가 공급", "") == ["배추", "무"]
    assert t.tag("[물가 비상] 배추 52%·무 42% 껑충", "") == ["배추", "무"]
    assert "무" not in t.tag("무료 급식 확대…무름병 확산", "")
    assert t.tag("양파·마늘 할당관세 적용", "") == ["양파", "깐마늘"]
    assert t.tag("풋고추 가격 급등", "") == []


def test_typhoon_is_bullish_no_negation_flip():
    s = _fire("태풍 피해 우려에 산지 긴장", symbols=("무",))
    assert s["agri_typhoon"].direction == Direction.BULLISH


def test_reserve_buy_vs_release():
    buy = _fire("농식품부, 배추 2만톤 수매 확대·시장격리", symbols=("배추",))
    assert "agri_reserve_buy" in buy and "agri_reserve_release" not in buy
    rel = _fire("비축 배추 하루 200톤 방출", symbols=("배추",))
    assert "agri_reserve_release" in rel and "agri_reserve_buy" not in rel


def test_agri_tagger_title_first():
    from app.sources.agri_watchlist import AgriTagger

    tg = AgriTagger()
    # 제목에 품목 → 태깅
    assert tg.tag("배추 ‘청명가을’, 대한민국 최고 품종 대통령상 수상", "") == ["배추"]
    # 요약 1회 언급만 → 미태깅 (2026-10-15 오탐 사례)
    assert tg.tag("[탐방] 감홍 사과 되살렸죠", "… 포기하지 않았다. 배추 농사도 잠깐 했다.") == []
    # 요약 2회 이상 → 태깅
    assert tg.tag("유통개선에 7779억원 투입", "양파 농가수취율… 양파 가격이…") == ["양파"]
    # 레시피 문맥 veto
    assert tg.tag("김치찌개 레시피", "배추 배추 배추") == []
