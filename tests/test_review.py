"""review 레이어 단위 테스트.

커버 대상:
  app/review/models.py
  app/review/checks.py
  app/review/reporter.py
"""

import json
from datetime import datetime, timezone

from app.review.checks import (
    _check_duplicate_hash,
    _check_misclassification,
    _check_no_summary,
    _check_untagged_watchlist,
    detect_issues,
)
from app.review.models import (
    ISSUE_LABEL,
    ArticleIssue,
    IssueKind,
    ReviewArticle,
    ReviewResult,
)
from app.review.reporter import render_json, render_text

_NOW = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
_SINCE = datetime(2024, 5, 31, 21, 0, 0, tzinfo=timezone.utc)
_UNTIL = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


def _make_article(
    article_id=1,
    title="테스트 기사",
    summary="요약 텍스트",
    article_type="market",
    title_hash="abc123",
    symbols=None,
    published_at=None,
):
    return ReviewArticle(
        id=article_id,
        title=title,
        url=f"https://example.com/{article_id}",
        source_name="테스트소스",
        summary=summary,
        article_type=article_type,
        published_at=published_at,
        collected_at=_NOW,
        title_hash=title_hash,
        symbols=symbols or [],
    )


def _make_result(articles=None, issues=None):
    return ReviewResult(since=_SINCE, until=_UNTIL, articles=articles or [], issues=issues or [])


class TestIssueKind:
    def test_enum_values(self):
        assert IssueKind.NO_SUMMARY.value == "no_summary"
        assert IssueKind.DUPLICATE_HASH.value == "duplicate_hash"
        assert IssueKind.UNTAGGED_WATCHLIST.value == "untagged_watchlist"
        assert IssueKind.MISCLASSIFICATION.value == "misclassification"

    def test_issue_label_완전성(self):
        for kind in IssueKind:
            assert kind in ISSUE_LABEL


class TestReviewArticle:
    def test_기본_생성(self):
        a = _make_article()
        assert a.id == 1 and a.symbols == []

    def test_symbols_포함(self):
        assert _make_article(symbols=["NVDA"]).symbols == ["NVDA"]

    def test_published_at_none(self):
        assert _make_article(published_at=None).published_at is None


class TestArticleIssue:
    def test_생성(self):
        issue = ArticleIssue(article_id=1, kind=IssueKind.NO_SUMMARY, detail="요약 없음")
        assert issue.article_id == 1 and issue.kind == IssueKind.NO_SUMMARY


class TestReviewResult:
    def test_stats_집계(self):
        articles = [
            _make_article(article_id=1, article_type="market"),
            _make_article(article_id=2, article_type="market"),
            _make_article(article_id=3, article_type="company"),
        ]
        stats = _make_result(articles=articles).stats
        assert stats["market"] == 2 and stats["company"] == 1

    def test_stats_빈기사(self):
        assert _make_result().stats == {}

    def test_issues_by_kind(self):
        issues = [
            ArticleIssue(article_id=1, kind=IssueKind.NO_SUMMARY, detail="d1"),
            ArticleIssue(article_id=2, kind=IssueKind.NO_SUMMARY, detail="d2"),
            ArticleIssue(article_id=3, kind=IssueKind.DUPLICATE_HASH, detail="d3"),
        ]
        by_kind = _make_result(issues=issues).issues_by_kind
        assert len(by_kind[IssueKind.NO_SUMMARY]) == 2
        assert len(by_kind[IssueKind.DUPLICATE_HASH]) == 1

    def test_articles_by_id(self):
        articles = [_make_article(article_id=i) for i in range(1, 4)]
        by_id = _make_result(articles=articles).articles_by_id
        assert 1 in by_id and 3 in by_id

    def test_articles_by_type(self):
        articles = [
            _make_article(article_id=1, article_type="market"),
            _make_article(article_id=2, article_type="event"),
        ]
        by_type = _make_result(articles=articles).articles_by_type
        assert len(by_type["market"]) == 1 and len(by_type["event"]) == 1

    def test_issue_article_ids(self):
        issues = [
            ArticleIssue(article_id=1, kind=IssueKind.NO_SUMMARY, detail="d"),
            ArticleIssue(article_id=1, kind=IssueKind.DUPLICATE_HASH, detail="d"),
            ArticleIssue(article_id=3, kind=IssueKind.NO_SUMMARY, detail="d"),
        ]
        assert _make_result(issues=issues).issue_article_ids == {1, 3}


class TestCheckNoSummary:
    def test_요약없는_기사_감지(self):
        issues = _check_no_summary(
            [_make_article(summary=""), _make_article(article_id=2, summary="있음")]
        )
        assert len(issues) == 1 and issues[0].kind == IssueKind.NO_SUMMARY

    def test_공백만있는_요약도_감지(self):
        assert len(_check_no_summary([_make_article(summary="   ")])) == 1

    def test_요약있으면_빈리스트(self):
        assert _check_no_summary([_make_article(summary="요약 있음")]) == []


class TestCheckDuplicateHash:
    def test_동일해시_감지(self):
        articles = [
            _make_article(article_id=1, title_hash="hash1"),
            _make_article(article_id=2, title_hash="hash1"),
        ]
        issues = _check_duplicate_hash(articles)
        assert len(issues) == 2 and all(i.kind == IssueKind.DUPLICATE_HASH for i in issues)

    def test_해시없으면_감지안함(self):
        articles = [_make_article(article_id=i, title_hash="") for i in range(1, 3)]
        assert _check_duplicate_hash(articles) == []

    def test_해시다르면_감지안함(self):
        articles = [
            _make_article(article_id=1, title_hash="h1"),
            _make_article(article_id=2, title_hash="h2"),
        ]
        assert _check_duplicate_hash(articles) == []

    def test_3건_중복(self):
        articles = [_make_article(article_id=i, title_hash="same") for i in range(1, 4)]
        assert len(_check_duplicate_hash(articles)) == 3


class TestCheckUntaggedWatchlist:
    def test_nvidia_키워드_태그없으면_감지(self):
        issues = _check_untagged_watchlist([_make_article(title="엔비디아 주가 급등", symbols=[])])
        assert len(issues) == 1 and issues[0].kind == IssueKind.UNTAGGED_WATCHLIST

    def test_이미_태깅된_기사_제외(self):
        assert (
            _check_untagged_watchlist([_make_article(title="엔비디아 주가 급등", symbols=["NVDA"])])
            == []
        )

    def test_관심종목_없는_기사(self):
        assert _check_untagged_watchlist([_make_article(title="무관한 일반 기사")]) == []


class TestCheckMisclassification:
    def test_분류불일치_감지(self):
        articles = [_make_article(title="삼성전자 earnings beat 실적 발표", article_type="general")]
        issues = _check_misclassification(articles)
        assert len(issues) == 1 and issues[0].kind == IssueKind.MISCLASSIFICATION

    def test_분류일치하면_이슈없음(self):
        assert (
            _check_misclassification(
                [_make_article(title="삼성전자 earnings beat", article_type="company")]
            )
            == []
        )

    def test_분류기가_general_반환하면_이슈없음(self):
        assert (
            _check_misclassification([_make_article(title="일반적인 뉴스", article_type="event")])
            == []
        )


class TestDetectIssues:
    def test_정상_기사(self):
        assert detect_issues([_make_article(summary="요약 있음")]) == []

    def test_복합_이슈(self):
        articles = [
            _make_article(article_id=1, summary="", title_hash="dup"),
            _make_article(article_id=2, summary="", title_hash="dup"),
        ]
        kinds = {i.kind for i in detect_issues(articles)}
        assert IssueKind.NO_SUMMARY in kinds and IssueKind.DUPLICATE_HASH in kinds

    def test_빈_목록(self):
        assert detect_issues([]) == []


class TestRenderText:
    def test_이슈없을때_정상메시지(self):
        assert "이슈 없음" in render_text(_make_result(articles=[_make_article()]))

    def test_이슈있을때_헤더(self):
        articles = [_make_article(summary="")]
        result = _make_result(articles=articles, issues=detect_issues(articles))
        assert "발견된 이슈" in render_text(result)

    def test_market_섹션(self):
        assert "MARKET" in render_text(
            _make_result(articles=[_make_article(article_type="market")])
        )

    def test_company_섹션(self):
        assert "COMPANY" in render_text(
            _make_result(articles=[_make_article(article_type="company")])
        )

    def test_event_섹션(self):
        assert "EVENT" in render_text(_make_result(articles=[_make_article(article_type="event")]))

    def test_general_섹션(self):
        assert "GENERAL" in render_text(
            _make_result(articles=[_make_article(article_type="general")])
        )

    def test_알수없는_타입도_렌더링(self):
        text = render_text(_make_result(articles=[_make_article(article_type="custom_type")]))
        assert "CUSTOM_TYPE" in text

    def test_이슈_detail_표시(self):
        articles = [_make_article(summary="")]
        issues = [ArticleIssue(article_id=1, kind=IssueKind.NO_SUMMARY, detail="요약 없음")]
        result = _make_result(articles=articles, issues=issues)
        assert "이슈 상세 목록" in render_text(result)

    def test_요약없는_기사(self):
        assert "요약 없음" in render_text(_make_result(articles=[_make_article(summary="")]))

    def test_published_at_없는_기사(self):
        assert isinstance(
            render_text(_make_result(articles=[_make_article(published_at=None)])), str
        )

    def test_symbols_있는_기사(self):
        assert "NVDA" in render_text(_make_result(articles=[_make_article(symbols=["NVDA"])]))

    def test_긴_제목_잘림(self):
        assert "…" in render_text(_make_result(articles=[_make_article(title="가" * 100)]))

    def test_빈_기사목록(self):
        assert isinstance(render_text(_make_result()), str)


class TestRenderJson:
    def test_유효한_json(self):
        result = _make_result(articles=[_make_article()])
        data = json.loads(render_json(result))
        assert "articles" in data and len(data["articles"]) == 1

    def test_since_until_포함(self):
        data = json.loads(render_json(_make_result()))
        assert "since" in data and "until" in data

    def test_이슈_포함(self):
        articles = [_make_article(summary="")]
        issues = [ArticleIssue(article_id=1, kind=IssueKind.NO_SUMMARY, detail="요약 없음")]
        data = json.loads(render_json(_make_result(articles=articles, issues=issues)))
        assert data["total_issues"] == 1

    def test_article_published_at_none(self):
        data = json.loads(render_json(_make_result(articles=[_make_article(published_at=None)])))
        assert data["articles"][0]["published_at"] is None

    def test_symbols_포함(self):
        data = json.loads(render_json(_make_result(articles=[_make_article(symbols=["NVDA"])])))
        assert data["articles"][0]["symbols"] == ["NVDA"]
