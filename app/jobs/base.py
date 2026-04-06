"""Job 공통 모델 및 로깅 유틸리티.

JobResult: 모든 job의 표준 반환 구조.
setup_job_logging: 콘솔 + 파일 핸들러를 동시에 구성.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# 결과 모델
# ---------------------------------------------------------------------------


@dataclass
class JobResult:
    """Job 실행 결과.

    Attributes:
        job_name: job 식별자 (예: "collect", "briefing")
        success: 정상 종료 여부
        started_at: 시작 시각 (UTC)
        finished_at: 종료 시각 (UTC). 실행 전이면 None.
        detail: 결과 요약 메시지
        error: 예외 객체 (성공 시 None)
    """

    job_name: str
    success: bool
    started_at: datetime
    finished_at: datetime | None = None
    detail: str = ""
    error: Exception | None = field(default=None, repr=False)

    @property
    def elapsed_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def log_summary(self, logger: logging.Logger) -> None:
        status = "완료" if self.success else "실패"
        elapsed = f" | {self.elapsed_seconds:.1f}s" if self.elapsed_seconds is not None else ""
        detail = f" | {self.detail}" if self.detail else ""
        level = logging.INFO if self.success else logging.ERROR
        logger.log(level, "[%s] %s%s%s", self.job_name, status, elapsed, detail)
        if self.error:
            logger.error("  오류: %s", self.error)

    @property
    def exit_code(self) -> int:
        return 0 if self.success else 1


# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------


def setup_job_logging(
    job_name: str,
    log_level: str = "INFO",
    log_dir: str | Path | None = None,
) -> logging.Logger:
    """job용 루트 로거를 설정하고 반환한다.

    콘솔(stdout)과 파일(log_dir/job_YYYYMMDD.log)에 동시 출력한다.
    log_dir가 None이면 파일 핸들러는 추가하지 않는다.

    Args:
        job_name: job 식별자 (로그 파일명, 로그 메시지 접두어)
        log_level: 로그 레벨 문자열 (기본 "INFO")
        log_dir: 로그 파일 저장 디렉토리. None이면 파일 저장 없음.

    Returns:
        job 전용 Logger
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 루트 로거 초기화 (중복 핸들러 방지)
    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    console_h = logging.StreamHandler(sys.stdout)
    console_h.setFormatter(fmt)
    root.addHandler(console_h)

    # 파일 핸들러
    if log_dir is not None:
        log_path = _log_file_path(job_name, log_dir)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_h = logging.FileHandler(log_path, encoding="utf-8")
        file_h.setFormatter(fmt)
        root.addHandler(file_h)

    root.setLevel(level)
    logger = logging.getLogger(f"jobs.{job_name}")
    logger.info("로그 파일: %s", _log_file_path(job_name, log_dir) if log_dir else "(파일 없음)")
    return logger


def _log_file_path(job_name: str, log_dir: str | Path) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Path(log_dir) / f"{job_name}_{date_str}.log"
