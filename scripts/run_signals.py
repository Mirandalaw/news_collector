"""투자 시그널 분석 실행 진입점.

사용법:
  python scripts/run_signals.py                    # 최근 12시간 분석 (콘솔)
  python scripts/run_signals.py --hours 24         # 최근 24시간
  python scripts/run_signals.py --save             # 파일 저장
  python scripts/run_signals.py --fmt json --save  # JSON 저장
  python scripts/run_signals.py --no-console --save  # 콘솔 없이 파일만

브리핑 파이프라인과 통합:
  run_briefing.py와 동일한 BriefingService를 사용하므로
  기존 watchlist / symbols 설정이 그대로 적용됩니다.

환경변수:
  DB_*                  — DB 접속
  BRIEFING_HOURS_BACK   — 조회 시간 범위 (기본: 12)
  BRIEFING_OUTPUT_DIR   — 파일 저장 경로 (기본: output/)
  LOG_LEVEL             — 기본 WARNING
"""

import argparse
import os
import sys
from datetime import timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import DatabaseConfig
from app.services.briefing_service import BriefingQuery, BriefingService
from app.signals.engine import SignalEngine
from app.signals.reporter import render_json, render_text
from app.sources.watchlist import DEFAULT_WATCHLIST
from app.utils.datetime_utils import morning_briefing_window


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="투자 시그널 분석")

    parser.add_argument(
        "--hours", type=int,
        default=int(os.environ.get("BRIEFING_HOURS_BACK", "12")),
        help="조회 시간 범위 (기본: 12)",
    )
    parser.add_argument("--no-symbols", action="store_true",
                        help="관심 종목 필터 없이 전체 태깅 기사 분석")
    parser.add_argument("--fmt", default="text", choices=["text", "json"])
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--save-dir", default=os.environ.get("BRIEFING_OUTPUT_DIR", "output"))
    parser.add_argument("--no-console", action="store_true")
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING"))

    return parser.parse_args()


def _setup_logging(level_name: str) -> None:
    import logging
    level = getattr(logging, level_name.upper(), logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    args = _parse_args()
    _setup_logging(args.log_level)

    db_config = DatabaseConfig.from_env()
    symbols = [] if args.no_symbols else [w.symbol for w in DEFAULT_WATCHLIST]

    since, until = morning_briefing_window(hours_back=args.hours)
    query = BriefingQuery(since=since, until=until, symbols=symbols)

    briefing_result = BriefingService(db_config).run(query)
    report = SignalEngine().analyze(briefing_result)

    content = render_json(report) if args.fmt == "json" else render_text(report)

    if not args.no_console:
        print(content)

    if args.save:
        KST = timezone(timedelta(hours=9))
        date_str = since.astimezone(KST).strftime("%Y%m%d")
        ext = "json" if args.fmt == "json" else "txt"
        out_dir = Path(args.save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"signals_{date_str}.{ext}"
        out_path.write_text(content, encoding="utf-8")
        print(f"\n[저장 완료] {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
