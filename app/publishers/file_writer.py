"""파일 저장 Publisher.

브리핑을 텍스트(.txt) 또는 JSON(.json) 파일로 저장한다.

파일명 규칙:
  briefing_YYYYMMDD.txt   (텍스트 모드)
  briefing_YYYYMMDD.json  (JSON 모드)

같은 날짜에 재실행하면 덮어쓴다.
디렉토리가 없으면 자동 생성한다.
"""

import json
import logging
from pathlib import Path

from app.briefing.models import MorningBriefing
from app.publishers.base import PublishResult

logger = logging.getLogger(__name__)

_VALID_FORMATS = ("text", "json")


class FilePublisher:
    """브리핑을 파일로 저장하는 Publisher.

    Args:
        output_dir: 저장 디렉토리 경로 (기본: ./output)
        fmt: 파일 형식 — "text" 또는 "json"
    """

    def __init__(
        self,
        output_dir: str | Path = "output",
        fmt: str = "text",
    ) -> None:
        if fmt not in _VALID_FORMATS:
            raise ValueError(f"fmt은 {_VALID_FORMATS} 중 하나여야 합니다. 현재: {fmt!r}")
        self._output_dir = Path(output_dir)
        self._fmt = fmt

    @property
    def publisher_name(self) -> str:
        return f"file:{self._fmt}"

    def publish(self, briefing: MorningBriefing) -> PublishResult:
        path = self._resolve_path(briefing)
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            content = self._render(briefing)
            path.write_text(content, encoding="utf-8")
            resolved = str(path.resolve())
            logger.info("브리핑 파일 저장 | path=%s", resolved)
            return PublishResult(
                publisher=self.publisher_name,
                success=True,
                detail=resolved,
            )
        except OSError as e:
            logger.exception("파일 저장 실패 | path=%s", path)
            return PublishResult(
                publisher=self.publisher_name,
                success=False,
                detail=str(path),
                error=e,
            )

    # ---------------------------------------------------------------------------
    # 내부 헬퍼
    # ---------------------------------------------------------------------------

    def _resolve_path(self, briefing: MorningBriefing) -> Path:
        date_str = briefing.since.strftime("%Y%m%d")
        ext = "json" if self._fmt == "json" else "txt"
        return self._output_dir / f"briefing_{date_str}.{ext}"

    def _render(self, briefing: MorningBriefing) -> str:
        if self._fmt == "json":
            return json.dumps(briefing.to_dict(), ensure_ascii=False, indent=2)
        return briefing.to_text()
