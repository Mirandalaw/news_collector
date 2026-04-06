"""브리핑 품질 이슈 감지 로직.

각 감지 함수는 독립적으로 동작하며 ArticleIssue 목록을 반환한다.
detect_issues()가 모든 감지기를 통합해 실행한다.
"""

from collections import defaultdict

from app.classifiers.article_classifier import KeywordArticleClassifier
from app.review.models import ArticleIssue, IssueKind, ReviewArticle
from app.sources.watchlist import DEFAULT_WATCHLIST

# 미분류(general)는 재분류 이슈 감지 제외: 분류기도 general 반환이면 진짜 이슈가 아님.
# 분류기가 general이 아닌 명확한 레이블을 반환했는데 저장값과 다를 때만 이슈로 본다.
_CLASSIFIER = KeywordArticleClassifier()


def detect_issues(articles: list[ReviewArticle]) -> list[ArticleIssue]:
    """전체 이슈 감지를 실행하고 통합 결과를 반환한다.

    Args:
        articles: 검수 대상 기사 목록

    Returns:
        감지된 ArticleIssue 목록. 이슈 없으면 빈 리스트.
    """
    issues: list[ArticleIssue] = []
    issues.extend(_check_no_summary(articles))
    issues.extend(_check_duplicate_hash(articles))
    issues.extend(_check_untagged_watchlist(articles))
    issues.extend(_check_misclassification(articles))
    return issues


# ---------------------------------------------------------------------------
# 개별 감지기
# ---------------------------------------------------------------------------

def _check_no_summary(articles: list[ReviewArticle]) -> list[ArticleIssue]:
    """요약 텍스트가 비어 있는 기사를 감지한다."""
    return [
        ArticleIssue(
            article_id=a.id,
            kind=IssueKind.NO_SUMMARY,
            detail="summary 필드가 비어 있음 (RSS 원문에 요약 없음)",
        )
        for a in articles
        if not a.summary.strip()
    ]


def _check_duplicate_hash(articles: list[ReviewArticle]) -> list[ArticleIssue]:
    """동일 title_hash를 가진 기사를 중복 수집 의심으로 감지한다.

    title_hash가 없거나(빈 문자열) 단독으로 존재하는 경우는 제외한다.
    """
    hash_map: dict[str, list[ReviewArticle]] = defaultdict(list)
    for a in articles:
        if a.title_hash:
            hash_map[a.title_hash].append(a)

    issues: list[ArticleIssue] = []
    for dupes in hash_map.values():
        if len(dupes) < 2:
            continue
        all_ids = [str(d.id) for d in dupes]
        for a in dupes:
            other_ids = [i for i in all_ids if i != str(a.id)]
            issues.append(ArticleIssue(
                article_id=a.id,
                kind=IssueKind.DUPLICATE_HASH,
                detail=f"동일 title_hash 기사 id: {', '.join(other_ids)}",
            ))
    return issues


def _check_untagged_watchlist(articles: list[ReviewArticle]) -> list[ArticleIssue]:
    """관심 종목 키워드가 제목/요약에 있으나 태그가 없는 기사를 감지한다.

    이미 symbols가 태깅된 기사는 검사에서 제외한다.
    태거가 놓친 기사 = 태거 로직 개선 단서.
    """
    issues: list[ArticleIssue] = []
    for a in articles:
        if a.symbols:  # 이미 태깅됨
            continue
        text = f"{a.title} {a.summary}".lower()
        matched: list[str] = []
        for ws in DEFAULT_WATCHLIST:
            if any(kw in text for kw in ws.keywords):
                matched.append(ws.symbol)
        if matched:
            issues.append(ArticleIssue(
                article_id=a.id,
                kind=IssueKind.UNTAGGED_WATCHLIST,
                detail=f"감지된 종목 키워드: {', '.join(matched)} / 태그 없음",
            ))
    return issues


def _check_misclassification(articles: list[ReviewArticle]) -> list[ArticleIssue]:
    """키워드 재분류 결과와 저장된 article_type이 불일치하는 기사를 감지한다.

    분류기가 'general'을 반환하면 이슈로 보지 않는다.
    저장값이 'general'인데 분류기가 명확한 레이블을 반환한 경우는 이슈로 본다
    (태거 누락 가능성).
    """
    issues: list[ArticleIssue] = []
    for a in articles:
        inferred = _CLASSIFIER.classify(a.title, a.summary)
        if inferred == "general":
            continue  # 분류기도 확신 없으면 패스
        if inferred != a.article_type:
            issues.append(ArticleIssue(
                article_id=a.id,
                kind=IssueKind.MISCLASSIFICATION,
                detail=f"저장={a.article_type} / 키워드재분류={inferred}",
            ))
    return issues
