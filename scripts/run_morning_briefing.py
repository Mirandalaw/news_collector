"""아침 브리핑 생성 + 전송 실행 스크립트.

사용법:
  python scripts/run_morning_briefing.py                         # 콘솔 출력
  python scripts/run_morning_briefing.py --save                  # 파일 저장 (.txt)
  python scripts/run_morning_briefing.py --save --save-fmt json  # 파일 저장 (.json)
  python scripts/run_morning_briefing.py --telegram              # 텔레그램 전송
  python scripts/run_morning_briefing.py --save --telegram       # 파일 + 텔레그램 동시
  python scripts/run_morning_briefing.py --mock --hours 24       # MockSummarizer + 24시간

환경 변수:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD   — DB 접속 (선택)
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID              — 텔레그램 전송 시 필수
  LOG_LEVEL                                          — 기본 WARNING
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import DatabaseConfig
from app.publishers.console import ConsolePublisher
from app.publishers.file_writer import FilePublisher
from app.publishers.telegram import TelegramPublisher
from app.services.briefing_dispatcher import BriefingDispatcher
from app.services.briefing_service import BriefingQuery
from app.services.morning_briefing_service import MorningBriefingService
from app.sources.watchlist import DEFAULT_WATCHLIST
from app.summarizers.mock_summarizer import MockSummarizer
from app.utils.datetime_utils import morning_briefing_window


def _setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="아침 브리핑 생성 및 전송")

    # 전송 채널
    parser.add_argument("--save",      action="store_true", help="파일로 저장")
    parser.add_argument("--save-fmt",  default="text", choices=["text", "json"],
                        help="파일 형식 (기본: text)")
    parser.add_argument("--save-dir",  default="output", help="저장 디렉토리 (기본: output)")
    parser.add_argument("--telegram",  action="store_true", help="텔레그램으로 전송")
    parser.add_argument("--no-console", action="store_true",
                        help="콘솔 출력 비활성화 (파일/텔레그램 전용 실행 시)")

    # 조회 파라미터
    parser.add_argument("--hours",      type=int, default=12, help="조회 범위 (시간, 기본: 12)")
    parser.add_argument("--no-symbols", action="store_true",
                        help="관심 종목 필터 없이 전체 태깅 기사 조회")

    # 요약기
    parser.add_argument("--mock", action="store_true", help="MockSummarizer로 AI 요약 시뮬레이션")

    # 기타
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING"),
                        help="로그 레벨 (기본: WARNING)")

    return parser.parse_args()


def _build_publishers(args: argparse.Namespace) -> list:
    publishers = []

    if not args.no_console:
        publishers.append(ConsolePublisher())

    if args.save:
        publishers.append(FilePublisher(output_dir=args.save_dir, fmt=args.save_fmt))

    if args.telegram:
        publishers.append(TelegramPublisher())

    if not publishers:
        publishers.append(ConsolePublisher())

    return publishers


def main() -> int:
    args = _parse_args()
    _setup_logging(args.log_level)

    db_config  = DatabaseConfig.from_env()
    summarizer = MockSummarizer() if args.mock else None
    symbols    = [] if args.no_symbols else [w.symbol for w in DEFAULT_WATCHLIST]

    since, until = morning_briefing_window(hours_back=args.hours)
    query = BriefingQuery(since=since, until=until, symbols=symbols)

    service    = MorningBriefingService(db_config, summarizer=summarizer)
    publishers = _build_publishers(args)
    dispatcher = BriefingDispatcher(service, publishers)

    result = dispatcher.dispatch(query)

    if not result.all_succeeded:
        for r in result.failed_results:
            print(f"[FAIL] {r.publisher}: {r.detail}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
