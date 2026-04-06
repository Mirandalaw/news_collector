"""브리핑 품질 검수 데이터 모델."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IssueKind(str, Enum):
    """검수 이슈 유형.

    Attributes:
        NO_SUMMARY:         요약 텍스트가 비어 있는 기사
        DUPLICATE_HASH:     동일 title_hash가 같은 윈도우에 2건 이상 존재 (중복 수집 의심)
        UNTAGGED_WATCHLIST: 제목/요약에 관심 종목 키워드가 있으나 article_symbols 태그 없음
        MISCLASSIFICATION:  저장된 article_type과 키워드 재분류 결과가 불일치
    """

    NO_SUMMARY = "no_summary"
    DUPLICATE_HASH = "duplicate_hash"
    UNTAGGED_WATCHLIST = "untagged_watchlist"
    MISCLASSIFICATION = "misclassification"


# IssueKind별 한국어 설명
ISSUE_LABEL: dict[IssueKind, str] = {
    IssueKind.NO_SUMMARY:         "요약 없음",
    IssueKind.DUPLICATE_HASH:     "중복 수집 의심",
    IssueKind.UNTAGGED_WATCHLIST: "종목 태그 누락",
    IssueKind.MISCLASSIFICATION:  "분류 불일치",
}


@dataclass(frozen=True)
class ReviewArticle:
    """검수용 기사 DTO. DB에서 직접 읽은 원본 데이터.

    BriefingArticle과 달리 ai_summary 없이 DB 저장값만 포함한다.
    title_hash가 포함되어 중복 감지에 사용된다.
    """

    id: int
    title: str
    url: str
    source_name: str
    summary: str
    article_type: str
    published_at: datetime | None
    collected_at: datetime
    title_hash: str
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArticleIssue:
    """단일 기사에 대한 검수 이슈.

    Attributes:
        article_id: 이슈가 발생한 기사 id
        kind:       이슈 유형
        detail:     사람이 읽을 수 있는 이슈 설명
    """

    article_id: int
    kind: IssueKind
    detail: str


@dataclass
class ReviewResult:
    """검수 실행 결과.

    Attributes:
        since:    조회 시작 시각 (UTC)
        until:    조회 종료 시각 (UTC)
        articles: 조회된 전체 기사 목록
        issues:   감지된 이슈 목록
    """

    since: datetime
    until: datetime
    articles: list[ReviewArticle]
    issues: list[ArticleIssue] = field(default_factory=list)

    # ------------------------------------------------------------------
    # 파생 뷰
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict[str, int]:
        """article_type별 기사 수 딕셔너리."""
        counts: dict[str, int] = defaultdict(int)
        for a in self.articles:
            counts[a.article_type] += 1
        return dict(counts)

    @property
    def issues_by_kind(self) -> dict[IssueKind, list[ArticleIssue]]:
        """IssueKind별로 그룹화된 이슈 딕셔너리."""
        grouped: dict[IssueKind, list[ArticleIssue]] = defaultdict(list)
        for issue in self.issues:
            grouped[issue.kind].append(issue)
        return dict(grouped)

    @property
    def articles_by_id(self) -> dict[int, ReviewArticle]:
        return {a.id: a for a in self.articles}

    @property
    def articles_by_type(self) -> dict[str, list[ReviewArticle]]:
        grouped: dict[str, list[ReviewArticle]] = defaultdict(list)
        for a in self.articles:
            grouped[a.article_type].append(a)
        return dict(grouped)

    @property
    def issue_article_ids(self) -> set[int]:
        """이슈가 하나라도 있는 기사 id 집합."""
        return {i.article_id for i in self.issues}
