"""jobs/base 단위 테스트.

커버 대상:
  app/jobs/base.py
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.jobs.base import JobResult, _log_file_path, setup_job_logging

_NOW = datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
_LATER = datetime(2024, 6, 1, 9, 0, 5, tzinfo=timezone.utc)


class TestJobResult:
    def test_기본_생성(self):
        result = JobResult(job_name="collect", success=True, started_at=_NOW)
        assert result.job_name == "collect"
        assert result.success is True
        assert result.finished_at is None

    def test_elapsed_seconds_없으면_none(self):
        result = JobResult(job_name="collect", success=True, started_at=_NOW)
        assert result.elapsed_seconds is None

    def test_elapsed_seconds_계산(self):
        result = JobResult(job_name="collect", success=True, started_at=_NOW, finished_at=_LATER)
        assert result.elapsed_seconds == 5.0

    def test_exit_code_성공(self):
        assert JobResult(job_name="collect", success=True, started_at=_NOW).exit_code == 0

    def test_exit_code_실패(self):
        assert JobResult(job_name="collect", success=False, started_at=_NOW).exit_code == 1

    def test_log_summary_성공(self):
        result = JobResult(
            job_name="collect",
            success=True,
            started_at=_NOW,
            finished_at=_LATER,
            detail="10건 수집",
        )
        result.log_summary(logging.getLogger("test"))

    def test_log_summary_실패_오류포함(self):
        result = JobResult(
            job_name="collect",
            success=False,
            started_at=_NOW,
            error=RuntimeError("DB 오류"),
        )
        result.log_summary(logging.getLogger("test"))

    def test_log_summary_elapsed_없을때(self):
        JobResult(job_name="collect", success=True, started_at=_NOW).log_summary(
            logging.getLogger("test")
        )

    def test_log_summary_detail_없을때(self):
        JobResult(job_name="collect", success=True, started_at=_NOW).log_summary(
            logging.getLogger("test")
        )


class TestSetupJobLogging:
    def test_로거_반환(self):
        assert isinstance(setup_job_logging("test_job", log_dir=None), logging.Logger)

    def test_log_dir_none이면_파일핸들러_없음(self):
        setup_job_logging("no_file_job", log_dir=None)
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_log_dir_지정시_파일_생성(self, tmp_path):
        setup_job_logging("file_job", log_dir=tmp_path)
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert tmp_path.exists()
        for h in file_handlers:
            h.close()
            root.removeHandler(h)

    def test_log_level_debug(self):
        setup_job_logging("debug_job", log_level="DEBUG", log_dir=None)
        assert logging.getLogger().level == logging.DEBUG

    def test_로거_이름_형식(self):
        logger = setup_job_logging("my_job", log_dir=None)
        assert "my_job" in logger.name


class TestLogFilePath:
    def test_경로_형식(self):
        path = _log_file_path("collect", "/tmp/logs")
        assert path.name.startswith("collect_")
        assert path.suffix == ".log"

    def test_Path_객체_입력(self, tmp_path):
        path = _log_file_path("briefing", tmp_path)
        assert isinstance(path, Path)
        assert "briefing_" in path.name
