"""job 실행 메트릭 조회 진입점.

사용법:
  python scripts/run_metrics.py             # 최근 30건 전체 job 이력
  python scripts/run_metrics.py --job collect   # collect job만
  python scripts/run_metrics.py --stats     # job별 7일 통계 요약
  python scripts/run_metrics.py --stats --days 30  # 30일 통계
  python scripts/run_metrics.py --limit 10  # 최근 10건만

환경변수:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  — DB 접속
"""

import argparse
import sys
from datetime import timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig, managed_connection
from app.db.repositories.metrics_repository import (
    JobMetricRow,
    JobStatRow,
    fetch_job_stats,
    fetch_recent_runs,
)

_W = 80
_KST = timezone(timedelta(hours=9))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="job 실행 메트릭 조회")
    parser.add_argument("--job", default=None, help="특정 job 이름 필터 (예: collect)")
    parser.add_argument("--limit", type=int, default=30, help="조회 건수 (기본: 30)")
    parser.add_argument("--stats", action="store_true", help="job별 통계 요약 출력")
    parser.add_argument("--days", type=int, default=7, help="--stats 집계 기간(일, 기본: 7)")
    return parser.parse_args()


def _fmt_dt(dt) -> str:
    if dt is None:
        return "-"
    return dt.astimezone(_KST).strftime("%m-%d %H:%M")


def _print_recent_runs(rows: list[JobMetricRow]) -> None:
    if not rows:
        print("  (조회된 이력 없음)")
        return

    header = f"{'#':>4}  {'job_name':<12}  {'started':>11}  {'elapsed':>8}  {'status':<6}  detail"
    print("─" * _W)
    print(header)
    print("─" * _W)
    for i, r in enumerate(rows, 1):
        status = "OK" if r.success else "FAIL"
        elapsed = f"{r.elapsed_secs:.1f}s" if r.elapsed_secs is not None else "-"
        detail = r.detail[:40] if r.detail else ""
        if r.error_msg:
            detail = f"[ERR] {r.error_msg[:35]}"
        print(
            f"{i:>4}  {r.job_name:<12}  {_fmt_dt(r.started_at):>11}  "
            f"{elapsed:>8}  {status:<6}  {detail}"
        )
    print("─" * _W)


def _print_stats(rows: list[JobStatRow], days: int) -> None:
    if not rows:
        print(f"  (최근 {days}일 이력 없음)")
        return

    print("─" * _W)
    print(f"  job별 통계  │  최근 {days}일")
    print("─" * _W)
    header = f"  {'job_name':<14}  {'총실행':>6}  {'성공':>5}  {'성공률':>7}  {'평균(s)':>8}  마지막 실행"
    print(header)
    print("─" * _W)
    for r in rows:
        rate = f"{r.success_runs / r.total_runs * 100:.0f}%" if r.total_runs else "-"
        avg = f"{r.avg_elapsed_secs:.1f}" if r.avg_elapsed_secs is not None else "-"
        last = _fmt_dt(r.last_run_at)
        print(
            f"  {r.job_name:<14}  {r.total_runs:>6}  {r.success_runs:>5}  "
            f"{rate:>7}  {avg:>8}  {last}"
        )
    print("─" * _W)


def main() -> int:
    args = _parse_args()
    db_config = DatabaseConfig.from_env()

    print(f"\n{'═' * _W}")
    print(f"  job 실행 메트릭  │  DB: {db_config.host}/{db_config.dbname}")
    print(f"{'═' * _W}")

    try:
        with managed_connection(db_config) as conn:
            if args.stats:
                rows = fetch_job_stats(conn, days=args.days)
                _print_stats(rows, args.days)
            else:
                rows = fetch_recent_runs(conn, job_name=args.job, limit=args.limit)
                filter_label = f" (job={args.job})" if args.job else ""
                print(f"\n  최근 {args.limit}건 이력{filter_label}")
                _print_recent_runs(rows)
    except Exception as e:
        print(f"\n[ERROR] DB 연결 또는 조회 실패: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
