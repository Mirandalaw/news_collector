"""브리핑 생성 + 전송 Job.

run_briefing(config) → JobResult

DB에서 기사를 조회해 브리핑을 생성하고 등록된 채널로 전송하는 단일 함수.
스크립트 / 스케줄러 어디서든 직접 호출 가능.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.db.connection import DatabaseConfig
from app.jobs.base import JobResult
from app.publishers.base import Publisher
from app.publishers.console import ConsolePublisher
from app.publishers.file_writer import FilePublisher
from app.publishers.telegram import TelegramPublisher
from app.services.briefing_dispatcher import BriefingDispatcher
from app.services.briefing_service import BriefingQuery
from app.services.morning_briefing_service import MorningBriefingService
from app.sources.watchlist import DEFAULT_WATCHLIST
from app.summarizers.base import Summarizer
from app.utils.datetime_utils import morning_briefing_window

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 브리핑 Job 설정
# ---------------------------------------------------------------------------

@dataclass
class BriefingJobConfig:
    """브리핑 Job 실행 파라미터.

    Attributes:
        hours_back: 조회 시간 범위 (기본 12시간)
        symbols: 관심 종목 코드 목록. 빈 리스트면 watchlist 전체 사용.
        summarizer: LLM 요약기. None이면 원본 summary 사용.
        publishers: 전달 채널 목록. 빈 리스트면 콘솔 출력.
    """

    hours_back: int = 12
    symbols: list[str] = field(default_factory=list)
    summarizer: Summarizer | None = None
    publishers: list[Publisher] = field(default_factory=list)

    def resolved_symbols(self) -> list[str]:
        """symbols가 비어 있으면 DEFAULT_WATCHLIST 전체를 반환한다."""
        return self.symbols or [w.symbol for w in DEFAULT_WATCHLIST]

    def resolved_publishers(self) -> list[Publisher]:
        """publishers가 비어 있으면 ConsolePublisher를 기본으로 반환한다."""
        return self.publishers or [ConsolePublisher()]


# ---------------------------------------------------------------------------
# 편의 팩토리
# ---------------------------------------------------------------------------

def build_publishers(
    console: bool = True,
    file_dir: str | None = None,
    file_fmt: str = "text",
    telegram: bool = False,
) -> list[Publisher]:
    """Publisher 목록을 플래그로 간결하게 구성한다.

    Args:
        console: 콘솔 출력 포함 여부
        file_dir: 파일 저장 디렉토리. None이면 파일 저장 없음.
        file_fmt: 파일 형식 ("text" 또는 "json")
        telegram: 텔레그램 전송 포함 여부 (환경 변수 설정 필요)

    Returns:
        Publisher 목록. 아무것도 없으면 ConsolePublisher 자동 포함.
    """
    publishers: list[Publisher] = []
    if console:
        publishers.append(ConsolePublisher())
    if file_dir is not None:
        publishers.append(FilePublisher(output_dir=file_dir, fmt=file_fmt))
    if telegram:
        publishers.append(TelegramPublisher())
    return publishers or [ConsolePublisher()]


# ---------------------------------------------------------------------------
# Job 진입점
# ---------------------------------------------------------------------------

def run_briefing(
    db_config: DatabaseConfig,
    job_config: BriefingJobConfig | None = None,
) -> JobResult:
    """브리핑 생성 + 전송 파이프라인을 실행하고 JobResult를 반환한다.

    Args:
        db_config: DB 접속 설정
        job_config: 브리핑 Job 파라미터. None이면 기본값 사용.

    Returns:
        JobResult — exit_code 속성으로 프로세스 종료 코드 결정
    """
    cfg     = job_config or BriefingJobConfig()
    started = datetime.now(timezone.utc)

    since, until = morning_briefing_window(hours_back=cfg.hours_back)
    symbols = cfg.resolved_symbols()

    logger.info(
        "브리핑 생성 시작 | since=%s ~ until=%s | 종목=%d개 | 채널=%s",
        since.strftime("%Y-%m-%d %H:%M"),
        until.strftime("%H:%M UTC"),
        len(symbols),
        [p.publisher_name for p in cfg.resolved_publishers()],
    )

    try:
        query      = BriefingQuery(since=since, until=until, symbols=symbols)
        service    = MorningBriefingService(db_config, summarizer=cfg.summarizer)
        dispatcher = BriefingDispatcher(service, cfg.resolved_publishers())
        result     = dispatcher.dispatch(query)
    except Exception as e:
        logger.exception("브리핑 파이프라인 오류")
        return JobResult(
            job_name="briefing",
            success=False,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            detail="파이프라인 실행 실패",
            error=e,
        )

    finished  = datetime.now(timezone.utc)
    success   = result.all_succeeded
    b         = result.briefing
    channels  = len(result.publish_results)
    ok_count  = sum(1 for r in result.publish_results if r.success)

    detail = (
        f"market={b.market_section.count} / "
        f"symbol={b.symbol_section.count} / "
        f"event={b.event_section.count} | "
        f"채널 {ok_count}/{channels} 전송 성공"
    )

    if not success:
        for r in result.failed_results:
            logger.warning("전송 실패 채널: %s — %s", r.publisher, r.detail)

    logger.info("브리핑 완료 | %s", detail)

    return JobResult(
        job_name="briefing",
        success=success,
        started_at=started,
        finished_at=finished,
        detail=detail,
    )
