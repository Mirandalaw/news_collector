"""GitHub push webhook 서버.

push 이벤트 수신 → HMAC 서명 검증 → git pull → docker compose build

실행:
    python3 webhook_server.py

환경변수:
    WEBHOOK_SECRET   GitHub webhook secret (필수)
    WEBHOOK_PORT     수신 포트 (기본: 9000)
    PROJECT_DIR      프로젝트 경로 (기본: /opt/news-collector)
    DEPLOY_BRANCH    배포 대상 브랜치 (기본: main)
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
PROJECT_DIR = os.environ.get("PROJECT_DIR", "/opt/news-collector")
DEPLOY_BRANCH = os.environ.get("DEPLOY_BRANCH", "main")

# ---------------------------------------------------------------------------
# 로깅
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("webhook")

# ---------------------------------------------------------------------------
# 배포 로직
# ---------------------------------------------------------------------------

_deploy_lock = threading.Lock()


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """명령어를 실행하고 (returncode, stdout, stderr)를 반환한다."""
    result = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _is_up_to_date(output: str) -> bool:
    normalized = output.strip().rstrip(".")
    return normalized == "Already up to date"


def deploy() -> bool:
    """git pull → docker compose build → db 재시작을 순서대로 실행한다.

    Returns:
        True: 성공, False: 실패
    """
    if not _deploy_lock.acquire(blocking=False):
        logger.warning("배포 이미 진행 중 — 요청 무시")
        return False

    try:
        logger.info("배포 시작 | dir=%s | branch=%s", PROJECT_DIR, DEPLOY_BRANCH)

        # 1. git pull
        code, out, err = _run(["git", "pull", "origin", DEPLOY_BRANCH])
        if code != 0:
            logger.error("git pull 실패 (code=%d)\nstdout: %s\nstderr: %s", code, out, err)
            return False
        logger.info("git pull 완료\n%s", out)

        # 변경 없으면 build/재시작 스킵
        if _is_up_to_date(out):
            logger.info("변경 없음 — build 스킵")
            return True

        # 2. docker compose build
        code, out, err = _run(["docker", "compose", "build"])
        if code != 0:
            logger.error(
                "docker compose build 실패 (code=%d)\nstdout: %s\nstderr: %s", code, out, err
            )
            return False
        logger.info("docker compose build 완료")

        # 3. db 컨테이너 재시작 (스키마 변경 등 반영)
        code, out, err = _run(["docker", "compose", "up", "-d", "--no-deps", "db"])
        if code != 0:
            logger.warning("db 재시작 실패 (code=%d) — 무시하고 계속\nstderr: %s", code, err)

        logger.info("배포 완료")
        return True

    except subprocess.TimeoutExpired:
        logger.error("배포 타임아웃 (300s 초과)")
        return False
    except Exception:
        logger.exception("배포 중 예외 발생")
        return False
    finally:
        _deploy_lock.release()


# ---------------------------------------------------------------------------
# HMAC 검증
# ---------------------------------------------------------------------------


def _verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """GitHub X-Hub-Signature-256 헤더를 검증한다."""
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# HTTP 핸들러
# ---------------------------------------------------------------------------


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: N802
        logger.info("HTTP %s", fmt % args)

    def do_POST(self):  # noqa: N802
        if self.path != "/webhook":
            self._respond(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 서명 검증
        if SECRET:
            sig = self.headers.get("X-Hub-Signature-256", "")
            if not _verify_signature(SECRET, body, sig):
                logger.warning("서명 검증 실패 | IP=%s", self.client_address[0])
                self._respond(403, "Forbidden")
                return

        # 이벤트 타입 확인
        event = self.headers.get("X-GitHub-Event", "")
        if event != "push":
            logger.info("push 외 이벤트 무시 | event=%s", event)
            self._respond(200, "Ignored")
            return

        # 브랜치 확인
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, "Bad Request")
            return

        ref = payload.get("ref", "")
        pushed_branch = ref.removeprefix("refs/heads/")
        if pushed_branch != DEPLOY_BRANCH:
            logger.info("대상 브랜치 아님 — 무시 | ref=%s", ref)
            self._respond(200, "Ignored")
            return

        pusher = payload.get("pusher", {}).get("name", "unknown")
        commits = len(payload.get("commits", []))
        logger.info(
            "push 이벤트 수신 | pusher=%s | commits=%d | branch=%s",
            pusher,
            commits,
            pushed_branch,
        )

        # 배포는 별도 스레드에서 (HTTP 응답 먼저 반환)
        self._respond(200, "Deploying")
        threading.Thread(target=deploy, daemon=True).start()

    def _respond(self, code: int, message: str) -> None:
        body = message.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------


def main() -> None:
    if not SECRET:
        logger.warning("WEBHOOK_SECRET 미설정 — 서명 검증 없이 실행 중 (보안 위험)")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info(
        "webhook 서버 시작 | port=%d | dir=%s | branch=%s",
        PORT,
        PROJECT_DIR,
        DEPLOY_BRANCH,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("서버 종료")
        server.server_close()


if __name__ == "__main__":
    main()
