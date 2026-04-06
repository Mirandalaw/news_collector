"""텔레그램 전송 Publisher.

Telegram Bot API의 sendMessage 엔드포인트를 사용해 브리핑을 전송한다.

설정 (환경 변수):
  TELEGRAM_BOT_TOKEN : BotFather에서 발급받은 봇 토큰
  TELEGRAM_CHAT_ID   : 전송 대상 채팅 ID (개인 DM 또는 채널/그룹)

채팅 ID 확인 방법:
  1. 봇에게 아무 메시지를 보낸 후
  2. https://api.telegram.org/bot{TOKEN}/getUpdates 호출
  3. result[0].message.chat.id 값 사용

의존성: 표준 라이브러리(urllib)만 사용 — 추가 패키지 불필요.

메시지 길이 제한:
  Telegram은 메시지당 4096자 제한.
  초과 시 섹션 경계를 보존하며 청크로 분할 전송한다.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.briefing.models import MorningBriefing
from app.publishers.base import PublishResult

logger = logging.getLogger(__name__)

_API_URL   = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_CHARS = 4000   # Telegram 한도 4096에서 여유 확보
_TIMEOUT   = 10     # 초


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TelegramConfig:
    """텔레그램 접속 설정.

    Attributes:
        bot_token: BotFather 발급 토큰
        chat_id: 전송 대상 채팅 ID
    """

    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        """환경 변수에서 설정을 읽는다."""
        return cls(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

class TelegramPublisher:
    """브리핑을 텔레그램으로 전송하는 Publisher.

    Args:
        config: TelegramConfig 인스턴스.
                None이면 환경 변수에서 자동으로 읽는다.
    """

    def __init__(self, config: TelegramConfig | None = None) -> None:
        self._config = config or TelegramConfig.from_env()

    @property
    def publisher_name(self) -> str:
        return "telegram"

    def publish(self, briefing: MorningBriefing) -> PublishResult:
        if not self._config.is_configured:
            return PublishResult(
                publisher=self.publisher_name,
                success=False,
                detail=(
                    "TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경 변수가 없습니다. "
                    "설정 후 재실행하세요."
                ),
            )

        chunks = _split_text(briefing.to_text())
        sent = 0
        try:
            for chunk in chunks:
                _send_message(self._config, chunk)
                sent += 1
            logger.info(
                "텔레그램 전송 완료 | chat_id=%s | %d개 청크",
                self._config.chat_id, sent,
            )
            return PublishResult(
                publisher=self.publisher_name,
                success=True,
                detail=f"chat_id={self._config.chat_id} | {sent}개 메시지 전송",
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            logger.error("텔레그램 HTTP 오류 | status=%d | body=%s", e.code, body[:200])
            return PublishResult(
                publisher=self.publisher_name,
                success=False,
                detail=f"HTTP {e.code} — {sent}/{len(chunks)} 청크 전송 후 실패",
                error=e,
            )
        except urllib.error.URLError as e:
            logger.error("텔레그램 네트워크 오류 | reason=%s", e.reason)
            return PublishResult(
                publisher=self.publisher_name,
                success=False,
                detail=f"네트워크 오류 — {sent}/{len(chunks)} 청크 전송 후 실패",
                error=e,
            )


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _send_message(config: TelegramConfig, text: str) -> None:
    """Telegram sendMessage API를 호출한다."""
    url     = _API_URL.format(token=config.bot_token)
    payload = json.dumps({"chat_id": config.chat_id, "text": text}).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
        logger.debug("텔레그램 응답 | status=%d", resp.status)


def _split_text(text: str, max_len: int = _MAX_CHARS) -> list[str]:
    """텍스트를 max_len 이하의 청크로 분할한다.

    줄 단위로 잘라서 메시지 중간에서 끊기지 않도록 한다.
    """
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > max_len and current_lines:
            chunks.append("".join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += len(line)

    if current_lines:
        chunks.append("".join(current_lines))

    return chunks
