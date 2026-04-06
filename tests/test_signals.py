"""시그널 레이어 단위 테스트.

커버 대상:
  app/signals/models.py
  app/signals/reporter.py
  app/signals/rules/base.py
  app/signals/rules/registry.py  (+ market_rules, symbol_rules)
  app/signals/engine.py
"""

import json
from datetime import datetime, timezone

from app.db.repositories.briefing_repository import BriefingArticle
from app.services.briefing_service import BriefingQuery, BriefingResult
from app.signals.engine import SignalEngine, _collect_unique
from app.signals.models import (
    DIRECTION_ICON,
    DIRECTION_LABEL,
    HORIZON_LABEL,
    IMPORTANCE_LABEL,
    Direction,
    Horizon,
    Importance,
    Signal,
    SignalReport,
)
from app.signals.reporter import render_json, render_text
from app.signals.rules import registry
from app.signals.rules.base import KeywordSignalRule

_NOW = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
_SINCE = datetime(2024, 5, 31, 21, 0, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


def _make_article(
    article_id=1, title="테스트 기사", summary="", article_type="market", symbols=None
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
        ai_summary="",
    )


def _make_signal(
    article_id=1,
    direction=None,
    horizon=None,
    importance=None,
    symbols=None,
    rule_name="test_rule",
    published_at=_NOW,
):
    return Signal(
        article_id=article_id,
        article_title="테스트 기사",
        rule_name=rule_name,
        direction=direction or Direction.BULLISH,
        horizon=horizon or Horizon.SHORT,
        importance=importance or Importance.MEDIUM,
        reason="테스트 근거",
        action_hint="테스트 힌트",
        symbols=symbols or [],
        source_name="테스트소스",
        published_at=published_at,
    )


def _make_report(signals=None, analyzed_count=0):
    return SignalReport(
        analyzed_at=_NOW,
        briefing_since=_SINCE,
        briefing_until=_UNTIL,
        signals=signals or [],
        analyzed_count=analyzed_count,
    )


def _make_briefing_result(market=None, symbol=None, event=None):
    query = BriefingQuery(since=_SINCE, until=_UNTIL)
    return BriefingResult(
        query=query,
        market_news=market or [],
        symbol_news=symbol or [],
        event_news=event or [],
    )


class TestEnums:
    def test_direction_values(self):
        assert Direction.BULLISH.value == "bullish"
        assert Direction.BEARISH.value == "bearish"
        assert Direction.NEUTRAL.value == "neutral"
        assert Direction.MIXED.value == "mixed"

    def test_horizon_values(self):
        assert Horizon.SHORT.value == "short"
        assert Horizon.LONG.value == "long"
        assert Horizon.BOTH.value == "both"

    def test_importance_values(self):
        assert Importance.HIGH.value == "high"
        assert Importance.MEDIUM.value == "medium"
        assert Importance.LOW.value == "low"

    def test_direction_label_완전성(self):
        for d in Direction:
            assert d in DIRECTION_LABEL

    def test_direction_icon_완전성(self):
        for d in Direction:
            assert d in DIRECTION_ICON

    def test_horizon_label_완전성(self):
        for h in Horizon:
            assert h in HORIZON_LABEL

    def test_importance_label_완전성(self):
        for i in Importance:
            assert i in IMPORTANCE_LABEL


class TestSignal:
    def test_기본_생성(self):
        s = _make_signal()
        assert s.article_id == 1
        assert s.direction == Direction.BULLISH

    def test_to_dict_구조(self):
        s = _make_signal(published_at=None)
        d = s.to_dict()
        assert d["direction"] == "bullish"
        assert d["horizon"] == "short"
        assert d["importance"] == "medium"
        assert d["published_at"] is None

    def test_to_dict_published_at_iso(self):
        d = _make_signal().to_dict()
        assert d["published_at"] == _NOW.isoformat()

    def test_symbols_포함(self):
        assert _make_signal(symbols=["NVDA"]).to_dict()["symbols"] == ["NVDA"]


class TestSignalReport:
    def test_빈_리포트(self):
        report = _make_report()
        assert len(report.signals) == 0

    def test_high_signals_필터(self):
        signals = [
            _make_signal(importance=Importance.HIGH, rule_name="h1"),
            _make_signal(importance=Importance.MEDIUM, rule_name="m1"),
            _make_signal(importance=Importance.HIGH, rule_name="h2"),
        ]
        assert len(_make_report(signals=signals).high_signals) == 2

    def test_by_horizon_both는_양쪽에_포함(self):
        signals = [
            _make_signal(horizon=Horizon.SHORT, rule_name="s1"),
            _make_signal(horizon=Horizon.LONG, rule_name="l1"),
            _make_signal(horizon=Horizon.BOTH, rule_name="b1"),
        ]
        by_h = _make_report(signals=signals).by_horizon
        assert len(by_h[Horizon.SHORT]) == 2
        assert len(by_h[Horizon.LONG]) == 2

    def test_by_symbol(self):
        signals = [
            _make_signal(symbols=["NVDA"], rule_name="r1"),
            _make_signal(symbols=["NVDA", "AAPL"], rule_name="r2"),
        ]
        by_sym = _make_report(signals=signals).by_symbol
        assert len(by_sym["NVDA"]) == 2
        assert len(by_sym["AAPL"]) == 1

    def test_market_signals(self):
        signals = [
            _make_signal(symbols=[], rule_name="market1"),
            _make_signal(symbols=["NVDA"], rule_name="sym1"),
        ]
        assert len(_make_report(signals=signals).market_signals) == 1

    def test_direction_summary(self):
        signals = [
            _make_signal(direction=Direction.BULLISH, rule_name="b1"),
            _make_signal(direction=Direction.BULLISH, rule_name="b2"),
            _make_signal(direction=Direction.BEARISH, rule_name="bear1"),
        ]
        summary = _make_report(signals=signals).direction_summary
        assert summary[Direction.BULLISH] == 2
        assert summary[Direction.BEARISH] == 1


class TestKeywordSignalRule:
    def _make_rule(self, **kwargs):
        defaults = dict(
            name="test_rule",
            trigger_keywords=("금리 인하",),
            direction=Direction.BULLISH,
            horizon=Horizon.SHORT,
            importance=Importance.MEDIUM,
            reason="근거",
            action_hint="힌트",
        )
        defaults.update(kwargs)
        return KeywordSignalRule(**defaults)

    def test_rule_name(self):
        assert self._make_rule(name="my_rule").rule_name == "my_rule"

    def test_트리거_매칭(self):
        assert self._make_rule().evaluate(_make_article(title="연준 금리 인하 시사")) is not None

    def test_트리거_없으면_none(self):
        assert self._make_rule().evaluate(_make_article(title="무관한 기사")) is None

    def test_disabled이면_none(self):
        assert self._make_rule(enabled=False).evaluate(_make_article(title="금리 인하")) is None

    def test_veto_키워드_있으면_none(self):
        rule = self._make_rule(veto_keywords=("금리 인상",))
        assert rule.evaluate(_make_article(title="금리 인하 기대 금리 인상 우려")) is None

    def test_target_types_불일치_none(self):
        rule = self._make_rule(target_types=("company",))
        assert rule.evaluate(_make_article(title="금리 인하", article_type="market")) is None

    def test_target_types_일치_시그널(self):
        rule = self._make_rule(target_types=("market",))
        assert rule.evaluate(_make_article(title="금리 인하", article_type="market")) is not None

    def test_target_symbols_불일치_none(self):
        rule = self._make_rule(target_symbols=("NVDA",))
        assert rule.evaluate(_make_article(title="금리 인하", symbols=["AAPL"])) is None

    def test_target_symbols_일치_시그널과_심볼_교집합(self):
        rule = self._make_rule(target_symbols=("NVDA",))
        signal = rule.evaluate(_make_article(title="금리 인하", symbols=["NVDA", "AAPL"]))
        assert signal is not None
        assert signal.symbols == ["NVDA"]

    def test_summary에서도_트리거_매칭(self):
        rule = self._make_rule()
        assert (
            rule.evaluate(_make_article(title="연준 발표", summary="금리 인하 가능성")) is not None
        )

    def test_article_symbols_상속(self):
        rule = self._make_rule()
        signal = rule.evaluate(_make_article(title="금리 인하", symbols=["NVDA", "AAPL"]))
        assert signal is not None
        assert set(signal.symbols) == {"NVDA", "AAPL"}


class TestRegistry:
    def test_기본_규칙_로드됨(self):
        assert len(registry.DEFAULT_RULES) > 0

    def test_모든_규칙_Protocol_준수(self):
        for rule in registry.DEFAULT_RULES:
            assert hasattr(rule, "rule_name") and hasattr(rule, "evaluate")

    def test_rule_names_중복_없음(self):
        names = [r.rule_name for r in registry.DEFAULT_RULES]
        assert len(names) == len(set(names))


class TestSignalEngine:
    def test_빈_브리핑(self):
        report = SignalEngine().analyze(_make_briefing_result())
        assert isinstance(report, SignalReport)
        assert report.analyzed_count == 0

    def test_매칭_기사_시그널_생성(self):
        rule = KeywordSignalRule(
            name="rate_cut",
            trigger_keywords=("금리 인하",),
            direction=Direction.BULLISH,
            horizon=Horizon.SHORT,
            importance=Importance.HIGH,
            reason="r",
            action_hint="h",
            target_types=("market",),
        )
        engine = SignalEngine(rules=[rule])
        article = _make_article(title="연준 금리 인하 결정", article_type="market")
        report = engine.analyze(_make_briefing_result(market=[article]))
        assert len(report.signals) == 1

    def test_중복_시그널_제거(self):
        rule = KeywordSignalRule(
            name="dup",
            trigger_keywords=("test",),
            direction=Direction.NEUTRAL,
            horizon=Horizon.SHORT,
            importance=Importance.LOW,
            reason="r",
            action_hint="h",
        )
        article = _make_article(title="test 기사")
        # 동일 기사가 market+symbol 양쪽에 있어도 _collect_unique가 1개만 분석
        report = SignalEngine(rules=[rule]).analyze(
            _make_briefing_result(market=[article], symbol=[article])
        )
        assert len(report.signals) == 1

    def test_규칙_예외_무시(self):
        class BrokenRule:
            @property
            def rule_name(self):
                return "broken"

            def evaluate(self, article):
                raise RuntimeError("의도적 예외")

        engine = SignalEngine(rules=[BrokenRule()])
        report = engine.analyze(_make_briefing_result(market=[_make_article()]))
        assert len(report.signals) == 0

    def test_시그널_정렬(self):
        rules = [
            KeywordSignalRule(
                name="low",
                trigger_keywords=("테스트",),
                direction=Direction.NEUTRAL,
                horizon=Horizon.SHORT,
                importance=Importance.LOW,
                reason="r",
                action_hint="h",
            ),
            KeywordSignalRule(
                name="high",
                trigger_keywords=("테스트",),
                direction=Direction.BULLISH,
                horizon=Horizon.SHORT,
                importance=Importance.HIGH,
                reason="r",
                action_hint="h",
            ),
        ]
        report = SignalEngine(rules=rules).analyze(
            _make_briefing_result(market=[_make_article(title="테스트 기사")])
        )
        assert len(report.signals) == 2
        assert report.signals[0].importance == Importance.HIGH


class TestCollectUnique:
    def test_중복_제거(self):
        a1 = _make_article(article_id=1)
        a2 = _make_article(article_id=2)
        result = _make_briefing_result(market=[a1], symbol=[a1, a2], event=[a2])
        unique = _collect_unique(result)
        assert {a.id for a in unique} == {1, 2}


class TestSignalReporter:
    def test_빈_리포트_텍스트(self):
        text = render_text(_make_report(analyzed_count=5))
        assert "시그널 리포트" in text
        assert "감지된 시그널이 없습니다" in text

    def test_high_시그널_있을때(self):
        signals = [_make_signal(direction=Direction.BULLISH, importance=Importance.HIGH)]
        text = render_text(_make_report(signals=signals, analyzed_count=3))
        assert "핵심 시그널" in text

    def test_단기_섹션(self):
        text = render_text(
            _make_report(signals=[_make_signal(horizon=Horizon.SHORT)], analyzed_count=1)
        )
        assert "단기" in text

    def test_장기_섹션(self):
        text = render_text(
            _make_report(signals=[_make_signal(horizon=Horizon.LONG)], analyzed_count=1)
        )
        assert "장기" in text

    def test_both_섹션(self):
        text = render_text(
            _make_report(signals=[_make_signal(horizon=Horizon.BOTH)], analyzed_count=1)
        )
        assert "단기" in text and "장기" in text

    def test_종목별_섹션(self):
        text = render_text(_make_report(signals=[_make_signal(symbols=["NVDA"])], analyzed_count=1))
        assert "NVDA" in text

    def test_published_at_없는_시그널(self):
        signal = _make_signal(published_at=None)
        text = render_text(_make_report(signals=[signal], analyzed_count=1))
        assert isinstance(text, str)

    def test_render_json_유효한_json(self):
        data = json.loads(render_json(_make_report(signals=[_make_signal()], analyzed_count=2)))
        assert len(data["signals"]) == 1
        assert data["analyzed_count"] == 2

    def test_render_json_빈_시그널(self):
        data = json.loads(render_json(_make_report()))
        assert data["total_signals"] == 0
