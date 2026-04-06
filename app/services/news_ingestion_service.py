"""뉴스 수집 → DB 저장 파이프라인 오케스트레이션 서비스.

RSS 수집(collector), 파싱(parser), DB 저장(repository)을 연결한다.
소스 단위로 수집과 저장을 처리해 한 소스의 실패가 전체를 중단시키지 않는다.
"""

import dataclasses
import logging
import time
from dataclasses import dataclass, field

import psycopg2

from app.classifiers.article_classifier import ArticleClassifier
from app.collectors.rss_collector import RssSource, collect_from_source
from app.db.connection import DatabaseConfig, managed_connection
from app.db.repositories.news_repository import NewsArticle, insert_articles
from app.db.repositories.symbol_repository import fetch_article_ids_by_urls, insert_article_symbols
from app.db.schema import create_tables
from app.services.dedup import DuplicateFilter, NullDuplicateFilter
from app.taggers.keyword_tagger import SymbolTagger

logger = logging.getLogger(__name__)


@dataclass
class SourceIngestionResult:
    """소스별 수집 + 저장 결과."""

    source_name: str
    collected: int = 0  # RSS에서 파싱된 기사 수
    inserted: int = 0  # DB에 신규 저장된 기사 수
    skipped: int = 0  # 중복으로 skip된 기사 수
    tagged: int = 0  # 1개 이상 종목이 태깅된 기사 수
    failed: bool = False
    error: str = ""


@dataclass
class IngestionReport:
    """전체 실행 결과 요약."""

    results: list[SourceIngestionResult] = field(default_factory=list)

    @property
    def total_collected(self) -> int:
        return sum(r.collected for r in self.results)

    @property
    def total_inserted(self) -> int:
        return sum(r.inserted for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    @property
    def total_tagged(self) -> int:
        return sum(r.tagged for r in self.results)

    @property
    def failed_sources(self) -> list[str]:
        return [r.source_name for r in self.results if r.failed]

    @property
    def all_failed(self) -> bool:
        """소스가 1개 이상이고 전체가 실패한 경우 True."""
        return bool(self.results) and all(r.failed for r in self.results)

    def log_summary(self) -> None:
        """결과 요약을 INFO 레벨로 출력한다."""
        logger.info("=" * 60)
        logger.info("[ 수집 결과 요약 ]")
        logger.info("  총 수집: %d건", self.total_collected)
        logger.info("  신규 저장: %d건", self.total_inserted)
        logger.info("  중복 스킵: %d건", self.total_skipped)
        logger.info("  종목 태깅: %d건", self.total_tagged)
        if self.failed_sources:
            logger.warning("  실패 소스: %s", ", ".join(self.failed_sources))
        else:
            logger.info("  실패 소스: 없음")

        for r in self.results:
            if r.failed:
                logger.warning(
                    "  [FAIL] %s | 수집=%d / 저장=%d / 스킵=%d | 오류: %s",
                    r.source_name,
                    r.collected,
                    r.inserted,
                    r.skipped,
                    r.error,
                )
            else:
                logger.info(
                    "  [OK]   %s | 수집=%d / 저장=%d / 스킵=%d / 태깅=%d",
                    r.source_name,
                    r.collected,
                    r.inserted,
                    r.skipped,
                    r.tagged,
                )
        logger.info("=" * 60)


class NewsIngestionService:
    """RSS 수집 → 파싱 → DB 저장 파이프라인.

    Args:
        db_config: PostgreSQL 접속 설정
        sources: 수집 대상 RSS 소스 목록
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        sources: list[RssSource],
        duplicate_filter: DuplicateFilter | None = None,
        symbol_tagger: SymbolTagger | None = None,
        article_classifier: ArticleClassifier | None = None,
    ) -> None:
        self._db_config = db_config
        self._sources = sources
        self._duplicate_filter: DuplicateFilter = duplicate_filter or NullDuplicateFilter()
        self._symbol_tagger: SymbolTagger | None = symbol_tagger
        self._article_classifier: ArticleClassifier | None = article_classifier

    def run(self) -> IngestionReport:
        """파이프라인 전체를 실행하고 결과 리포트를 반환한다.

        1. DB 커넥션 확보
        2. 테이블 보장 (CREATE IF NOT EXISTS)
        3. 소스별 수집 → 저장 루프
        4. 결과 집계 및 로그

        소스별 수집 실패 또는 DB 저장 실패는 continue로 처리한다.

        Returns:
            IngestionReport: 소스별 수집/저장 결과 집계

        Raises:
            psycopg2.OperationalError: DB 접속 자체가 불가능한 경우
        """
        report = IngestionReport()
        start = time.monotonic()

        logger.info("뉴스 수집 파이프라인 시작 | 소스 수=%d", len(self._sources))

        with managed_connection(self._db_config) as conn:
            create_tables(conn)

            for source in self._sources:
                result = self._process_source(conn, source)
                report.results.append(result)

        elapsed = time.monotonic() - start
        logger.info("파이프라인 종료 | 소요 시간=%.1f초", elapsed)
        report.log_summary()
        return report

    def _process_source(
        self,
        conn: "psycopg2.extensions.connection",
        source: RssSource,
    ) -> SourceIngestionResult:
        """단일 소스에 대해 수집 → 저장을 처리하고 결과를 반환한다.

        수집 또는 저장 중 예외가 발생해도 SourceIngestionResult(failed=True)를 반환하며
        예외를 상위로 전파하지 않는다.
        """
        ingestion = SourceIngestionResult(source_name=source.source_name)

        # 1. RSS 수집
        try:
            articles, collection_result = collect_from_source(source)
        except Exception as e:
            ingestion.failed = True
            ingestion.error = f"수집 오류: {e}"
            logger.error("수집 실패 - 건너뜀 | source=%s | error=%s", source.source_name, e)
            return ingestion

        ingestion.collected = collection_result.collected

        if collection_result.failed:
            ingestion.failed = True
            ingestion.error = f"수집 오류: {collection_result.error}"
            logger.warning(
                "소스 수집 실패 - 건너뜀 | source=%s | reason=%s",
                source.source_name,
                collection_result.error,
            )
            return ingestion

        if not articles:
            logger.info("저장 대상 없음 | source=%s", source.source_name)
            return ingestion

        # 2. 중복 필터 적용 (NullDuplicateFilter이면 no-op)
        articles = self._apply_dedup_filter(articles)

        # 3. 기사 분류 (classifier 미주입 시 skip → article_type="general" 유지)
        if self._article_classifier is not None:
            articles = self._classify_articles(articles)

        # 4. DB 저장
        try:
            inserted, skipped = insert_articles(conn, articles)
            ingestion.inserted = inserted
            ingestion.skipped = skipped
        except psycopg2.Error as e:
            ingestion.failed = True
            ingestion.error = f"DB 저장 오류: {e}"
            logger.error(
                "DB 저장 실패 - 건너뜀 | source=%s | error=%s",
                source.source_name,
                e,
            )
            return ingestion

        # 5. 종목 태깅 (tagger 미주입 시 skip)
        if self._symbol_tagger is not None and articles:
            ingestion.tagged = self._tag_articles(conn, articles)

        return ingestion

    def _tag_articles(
        self,
        conn: "psycopg2.extensions.connection",
        articles: list[NewsArticle],
    ) -> int:
        """기사 목록에 종목 태그를 부여하고 DB에 저장한다.

        - URL → article_id 매핑을 조회한 뒤 기사별로 태거를 호출한다.
        - 태깅/저장 실패는 기사 단위로 continue 처리하며 전체를 중단하지 않는다.
        - 트랜잭션은 소스별 commit으로 마무리한다.

        Returns:
            1개 이상의 종목이 태깅된 기사 수
        """
        assert self._symbol_tagger is not None

        tagged_count = 0
        try:
            url_to_id = fetch_article_ids_by_urls(conn, [a.url for a in articles])
        except psycopg2.Error:
            logger.exception("article_id 조회 실패 - 태깅 전체 스킵")
            return 0

        tagger_name = self._symbol_tagger.tagger_name

        for article in articles:
            article_id = url_to_id.get(article.url)
            if article_id is None:
                logger.debug("article_id 없음 - 태깅 스킵 | url=%s", article.url)
                continue

            try:
                symbols = self._symbol_tagger.tag(article.title, article.summary)
                if not symbols:
                    continue

                insert_article_symbols(conn, article_id, symbols, tagged_by=tagger_name)
                conn.commit()
                tagged_count += 1
                logger.debug("태깅 완료 | article_id=%d | symbols=%s", article_id, symbols)
            except psycopg2.Error:
                conn.rollback()
                logger.exception("태깅 저장 실패 - 스킵 | article_id=%d", article_id)
            except Exception:
                logger.exception("태깅 오류 - 스킵 | url=%s", article.url)

        if tagged_count:
            logger.info(
                "종목 태깅 완료 | 태깅된 기사=%d건 / 전체=%d건 | tagger=%s",
                tagged_count,
                len(articles),
                tagger_name,
            )

        return tagged_count

    def _classify_articles(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """분류기를 실행해 article_type이 설정된 새 NewsArticle 목록을 반환한다.

        NewsArticle은 frozen dataclass이므로 dataclasses.replace()로 재생성한다.
        분류 결과를 INFO 레벨로 집계해 출력한다.
        """
        assert self._article_classifier is not None

        classified: list[NewsArticle] = []
        counts: dict[str, int] = {}

        for article in articles:
            article_type = self._article_classifier.classify(article.title, article.summary)
            classified.append(dataclasses.replace(article, article_type=article_type))
            counts[article_type] = counts.get(article_type, 0) + 1

        if counts:
            breakdown = " / ".join(f"{t}={n}" for t, n in sorted(counts.items()))
            logger.info(
                "기사 분류 완료 | %d건 | %s | classifier=%s",
                len(classified),
                breakdown,
                self._article_classifier.classifier_name,
            )

        return classified

    def _apply_dedup_filter(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """중복 필터를 통과한 기사만 반환한다.

        NullDuplicateFilter이면 전체를 그대로 반환한다.
        필터링된 기사 수는 DEBUG 레벨로 로깅한다.
        """
        result: list[NewsArticle] = []
        for article in articles:
            if self._duplicate_filter.is_duplicate(article):
                logger.debug("타이틀 해시 중복 - 스킵 | title=%.50s", article.title)
                continue
            self._duplicate_filter.mark_seen(article)
            result.append(article)

        dropped = len(articles) - len(result)
        if dropped:
            logger.info("타이틀 해시 필터 | 제거=%d건 / 통과=%d건", dropped, len(result))

        return result
