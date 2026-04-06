"""job_metrics 테이블 대상 데이터 접근 모듈.

job 실행 이력을 기록하고 조회한다.
실패해도 job 자체에 영향을 주지 않도록 try_record_job_run()을 사용하는 것을 권장.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import psycopg2.extensions

from app.db.connection import DatabaseConfig, managed_connection

logger = logging.getLogger(__name__)

_INSERT_JOB_METRIC = """
INSERT INTO job_metrics
    (job_name, started_at, finished_at, success, elapsed_secs, detail, error_msg)
VALUES
    (%(job_name)s, %(started_at)s, %(finished_at)s, %(success)s,
     %(elapsed_secs)s, %(detail)s, %(error_msg)s);
"""

_SELECT_RECENT_RUNS = """
SELECT id, job_name, started_at, finished_at, success, elapsed_secs, detail, error_msg
FROM job_metrics
{where}
ORDER BY started_at DESC
LIMIT %(limit)s;
"""

_SELECT_STATS = """
SELECT
    job_name,
    COUNT(*)                                               AS total_runs,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)               AS success_runs,
    ROUND(AVG(elapsed_secs)::numeric, 1)                   AS avg_elapsed_secs,
    MAX(started_at)                                        AS last_run_at
FROM job_metrics
WHERE started_at >= NOW() - (%(days)s || ' days')::INTERVAL
GROUP BY job_name
ORDER BY job_name;
"""


@dataclass(frozen=True)
class JobMetricRow:
    """job_metrics 테이블 1행 DTO."""

    id: int
    job_name: str
    started_at: datetime
    finished_at: datetime | None
    success: bool
    elapsed_secs: float | None
    detail: str
    error_msg: str


@dataclass(frozen=True)
class JobStatRow:
    """job_name별 집계 통계."""

    job_name: str
    total_runs: int
    success_runs: int
    avg_elapsed_secs: float | None
    last_run_at: datetime


# ---------------------------------------------------------------------------
# 쓰기
# ---------------------------------------------------------------------------


def record_job_run(
    conn: psycopg2.extensions.connection,
    job_name: str,
    started_at: datetime,
    finished_at: datetime | None,
    success: bool,
    elapsed_secs: float | None,
    detail: str = "",
    error_msg: str = "",
) -> None:
    """job 실행 이력 1건을 job_metrics 테이블에 기록한다.

    Args:
        conn: psycopg2 커넥션 (autocommit=False)
        job_name: job 식별자
        started_at: 시작 시각 (UTC)
        finished_at: 종료 시각 (UTC). 미완료 시 None.
        success: 성공 여부
        elapsed_secs: 소요 시간(초). None이면 NULL 저장.
        detail: 결과 요약 문자열
        error_msg: 오류 메시지 (성공 시 빈 문자열)
    """
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_JOB_METRIC,
            {
                "job_name": job_name,
                "started_at": started_at,
                "finished_at": finished_at,
                "success": success,
                "elapsed_secs": elapsed_secs,
                "detail": detail or "",
                "error_msg": error_msg or "",
            },
        )
    conn.commit()
    logger.debug("job 메트릭 저장 | job=%s | success=%s", job_name, success)


def try_record_job_run(
    db_config: DatabaseConfig,
    job_name: str,
    started_at: datetime,
    finished_at: datetime | None,
    success: bool,
    elapsed_secs: float | None,
    detail: str = "",
    error_msg: str = "",
) -> None:
    """record_job_run의 안전한 래퍼. 실패해도 예외를 발생시키지 않는다.

    메트릭 저장 실패가 job 실행 결과에 영향을 주면 안 되므로
    스크립트 진입점에서는 이 함수를 사용하는 것을 권장한다.
    """
    try:
        with managed_connection(db_config) as conn:
            record_job_run(
                conn,
                job_name,
                started_at,
                finished_at,
                success,
                elapsed_secs,
                detail,
                error_msg,
            )
    except Exception:
        logger.warning("job 메트릭 저장 실패 (무시됨) | job=%s", job_name, exc_info=True)


# ---------------------------------------------------------------------------
# 읽기
# ---------------------------------------------------------------------------


def fetch_recent_runs(
    conn: psycopg2.extensions.connection,
    job_name: str | None = None,
    limit: int = 30,
) -> list[JobMetricRow]:
    """최근 job 실행 이력을 반환한다.

    Args:
        conn: psycopg2 커넥션
        job_name: 특정 job만 조회. None이면 전체.
        limit: 최대 반환 건수

    Returns:
        JobMetricRow 목록. 최신 순.
    """
    if job_name:
        where = "WHERE job_name = %(job_name)s"
        params: dict = {"job_name": job_name, "limit": limit}
    else:
        where = ""
        params = {"limit": limit}

    sql = _SELECT_RECENT_RUNS.format(where=where)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [_row_to_metric(r) for r in rows]


def fetch_job_stats(
    conn: psycopg2.extensions.connection,
    days: int = 7,
) -> list[JobStatRow]:
    """최근 N일 동안의 job별 통계를 반환한다.

    Args:
        conn: psycopg2 커넥션
        days: 집계 기간 (일)

    Returns:
        JobStatRow 목록. job_name 오름차순.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_STATS, {"days": days})
        rows = cur.fetchall()

    return [
        JobStatRow(
            job_name=r[0],
            total_runs=r[1],
            success_runs=r[2],
            avg_elapsed_secs=float(r[3]) if r[3] is not None else None,
            last_run_at=r[4],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _row_to_metric(row: tuple) -> JobMetricRow:
    return JobMetricRow(
        id=row[0],
        job_name=row[1],
        started_at=row[2],
        finished_at=row[3],
        success=row[4],
        elapsed_secs=float(row[5]) if row[5] is not None else None,
        detail=row[6] or "",
        error_msg=row[7] or "",
    )
