"""농산물 뉴스 수집 진입점 (해커톤 트랙 A·B).

기존 run_collect.py 와 같은 DB·파이프라인을 쓰되, 소스는 농업 전문지 RSS, 태깅은 5품목
watchlist 로 바꾼다. 경제 브리핑 쪽 동작은 바뀌지 않는다 (category="농업"으로 구분).

cron 예시 (하루 2회 — 보도자료·산지 기사가 오전·오후에 나뉘어 올라온다):
  0 9,16 * * *  /path/.venv/bin/python /path/scripts/run_agri_collect.py

옵션:
  --dump DIR   수집 직후 오늘 수집된 농업 기사를 DIR/YYYY-MM-DD.jsonl 로 스냅샷 저장
               (재현 검증용. 폐쇄망에서는 이 파일만 읽는다)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.classifiers.article_classifier import KeywordArticleClassifier
from app.db.connection import DatabaseConfig, managed_connection
from app.db.repositories.metrics_repository import try_record_job_run
from app.jobs.base import JobResult, setup_job_logging
from app.services.news_ingestion_service import NewsIngestionService
from app.sources.agri_sources import AGRI_CATEGORY, AGRI_SOURCES
from app.sources.agri_watchlist import AgriTagger

_DUMP_SQL = """
SELECT a.id, a.source_name, a.title, a.url, a.published_at, a.summary, a.collected_at,
       COALESCE(array_agg(s.symbol) FILTER (WHERE s.symbol IS NOT NULL), '{}') AS symbols
FROM news_articles a
LEFT JOIN article_symbols s ON s.article_id = a.id
WHERE a.category = %(cat)s AND a.collected_at::date = CURRENT_DATE
GROUP BY a.id
ORDER BY a.published_at;
"""


def dump_today(db_config: DatabaseConfig, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{datetime.now(timezone.utc).date()}.jsonl"
    n = 0
    with (
        managed_connection(db_config) as conn,
        conn.cursor() as cur,
        path.open("w", encoding="utf-8") as f,
    ):
        cur.execute(_DUMP_SQL, {"cat": AGRI_CATEGORY})
        for row in cur.fetchall():
            rec = dict(
                zip(
                    (
                        "id",
                        "source_name",
                        "title",
                        "url",
                        "published_at",
                        "summary",
                        "collected_at",
                        "symbols",
                    ),
                    row,
                )
            )
            for k in ("published_at", "collected_at"):
                rec[k] = rec[k].isoformat() if rec[k] else None
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="오늘 수집분 jsonl 스냅샷 저장 폴더")
    args = ap.parse_args()

    logger = setup_job_logging(
        "agri_collect", os.environ.get("LOG_LEVEL", "INFO"), os.environ.get("LOG_DIR", "logs")
    )
    db_config = DatabaseConfig.from_env()
    started = datetime.now(timezone.utc)
    try:
        report = NewsIngestionService(
            db_config=db_config,
            sources=AGRI_SOURCES,
            symbol_tagger=AgriTagger(),
            article_classifier=KeywordArticleClassifier(),
        ).run()
        detail = (
            f"수집={report.total_collected} / 저장={report.total_inserted} / "
            f"중복={report.total_skipped} / 품목태깅={report.total_tagged} / "
            f"실패소스={len(report.failed_sources)}/{len(AGRI_SOURCES)}"
        )
        if args.dump:
            detail += f" / 스냅샷={dump_today(db_config, Path(args.dump))}건"
        result = JobResult(
            job_name="agri_collect",
            success=not report.all_failed,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail=detail,
        )
    except Exception as e:  # DB 접속 실패 등
        logger.exception("농산물 수집 실패")
        result = JobResult(
            job_name="agri_collect",
            success=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail="파이프라인 실행 실패",
            error=e,
        )

    result.log_summary(logger)
    try_record_job_run(
        db_config=db_config,
        job_name=result.job_name,
        started_at=result.started_at,
        finished_at=result.finished_at,
        success=result.success,
        elapsed_secs=result.elapsed_seconds,
        detail=result.detail,
        error_msg=str(result.error) if result.error else "",
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
