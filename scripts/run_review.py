"""브리핑 품질 검수 실행 진입점.

사용법:
  python scripts/run_review.py                     # 어제 하루치 검수 (콘솔)
  python scripts/run_review.py --days 3            # 최근 3일치 검수
  python scripts/run_review.py --date 2026-04-05   # 특정 날짜 검수
  python scripts/run_review.py --save              # 파일 저장 (output/ 디렉토리)
  python scripts/run_review.py --fmt json --save   # JSON 형식 파일 저장
  python scripts/run_review.py --no-console --save # 콘솔 출력 없이 파일만

환경변수:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  — DB 접속
  LOG_LEVEL                                         — 기본 WARNING
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig
from app.review.reporter import render_json, render_text
from app.review.service import ReviewService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="브리핑 품질 검수")

    # 날짜 범위 (둘 중 하나만 사용)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--days",
        type=int,
        default=1,
        metavar="N",
        help="최근 N일치 검수 (기본: 1 = 어제 하루)",
    )
    group.add_argument(
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="특정 날짜 하루 검수 (KST 기준, --days와 함께 사용 불가)",
    )

    # 출력
    parser.add_argument("--fmt", default="text", choices=["text", "json"], help="출력 형식")
    parser.add_argument("--save", action="store_true", help="파일로 저장")
    parser.add_argument("--save-dir", default="output", help="저장 디렉토리 (기본: output)")
    parser.add_argument("--no-console", action="store_true", help="콘솔 출력 비활성화")

    # 기타
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="최대 조회 기사 수 (기본: 500)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "WARNING"),
        help="로그 레벨",
    )

    return parser.parse_args()


def _resolve_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    """CLI 인자로부터 (since, until) UTC datetime을 계산한다."""
    KST = timezone(timedelta(hours=9))
    today_kst = datetime.now(KST).date()

    if args.date:
        try:
            target: date = date.fromisoformat(args.date)
        except ValueError:
            print(
                f"[ERROR] --date 형식 오류: '{args.date}' (YYYY-MM-DD 형식 필요)", file=sys.stderr
            )
            sys.exit(1)
        # 지정 날짜 KST 00:00 ~ 다음날 KST 00:00
        since_kst = datetime(target.year, target.month, target.day, tzinfo=KST)
        until_kst = since_kst + timedelta(days=1)
    else:
        # 오늘 KST 기준 N일 전 00:00 ~ 오늘 00:00
        until_kst = datetime(today_kst.year, today_kst.month, today_kst.day, tzinfo=KST)
        since_kst = until_kst - timedelta(days=args.days)

    return since_kst.astimezone(timezone.utc), until_kst.astimezone(timezone.utc)


def _setup_logging(level_name: str) -> None:
    import logging

    level = getattr(logging, level_name.upper(), logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_to_file(content: str, save_dir: str, since: datetime, fmt: str) -> Path:
    """리포트를 파일로 저장하고 경로를 반환한다."""
    KST = timezone(timedelta(hours=9))
    date_str = since.astimezone(KST).strftime("%Y%m%d")
    ext = "json" if fmt == "json" else "txt"
    out_dir = Path(save_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"review_{date_str}.{ext}"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main() -> int:
    args = _parse_args()
    _setup_logging(args.log_level)

    since, until = _resolve_window(args)

    service = ReviewService(
        db_config=DatabaseConfig.from_env(),
        article_limit=args.limit,
    )
    result = service.run(since, until)

    # 렌더링
    if args.fmt == "json":
        content = render_json(result)
    else:
        content = render_text(result)

    # 출력
    if not args.no_console:
        print(content)

    if args.save:
        out_path = _save_to_file(content, args.save_dir, since, args.fmt)
        print(f"\n[저장 완료] {out_path}", file=sys.stderr)

    if not args.no_console and not args.save:
        pass  # 이미 콘솔에 출력됨

    # 이슈가 있으면 exit code 1 (cron / CI 연동 가능)
    return 1 if result.issues else 0


if __name__ == "__main__":
    sys.exit(main())
