"""배포 후 기본 동작 확인용 스모크 테스트.

성공 조건:
  1. DB 연결 가능
  2. 필수 테이블 존재 (news_articles)
  3. 뉴스 수집 코드 임포트 가능

종료 코드:
  0  모든 항목 통과
  1  하나 이상 실패

사용법:
  python scripts/smoke_test.py
  docker compose --profile tools run smoke
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


CHECKS: list[tuple[str, bool, str]] = []


def check(name: str):
    """데코레이터: 함수 실행 결과를 CHECKS에 기록한다."""

    def decorator(fn):
        def wrapper():
            try:
                fn()
                CHECKS.append((name, True, "OK"))
            except Exception as e:
                CHECKS.append((name, False, str(e)))

        return wrapper

    return decorator


# ── 1. DB 연결 ─────────────────────────────────────────────────
@check("DB 연결")
def _check_db_connection():
    from app.db.connection import DatabaseConfig, get_connection

    conn = get_connection(DatabaseConfig.from_env())
    conn.close()


# ── 2. 필수 테이블 존재 ────────────────────────────────────────
@check("테이블 존재: news_articles")
def _check_table_exists():
    from app.db.connection import DatabaseConfig, managed_connection

    with managed_connection(DatabaseConfig.from_env()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'news_articles'
            """)
            count = cur.fetchone()[0]
    if count == 0:
        raise RuntimeError("news_articles 테이블이 존재하지 않습니다. DB 스키마를 초기화하세요.")


# ── 3. 핵심 모듈 임포트 ────────────────────────────────────────
@check("모듈 임포트: collectors")
def _check_imports_collectors():
    from app.collectors.rss_collector import CollectionSummary  # noqa: F401


@check("모듈 임포트: briefing")
def _check_imports_briefing():
    from app.briefing.builder import build_morning_briefing  # noqa: F401
    from app.publishers.telegram import TelegramPublisher  # noqa: F401


# ── 4. 텔레그램 설정 확인 (경고만) ──────────────────────────────
@check("텔레그램 설정 확인")
def _check_telegram_config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정 (텔레그램 전송 비활성)")


# ── 실행 ───────────────────────────────────────────────────────
def main() -> int:
    runners = [
        _check_db_connection,
        _check_table_exists,
        _check_imports_collectors,
        _check_imports_briefing,
        _check_telegram_config,
    ]
    for fn in runners:
        fn()

    print("\n── Smoke Test 결과 ─────────────────────────────────")
    all_ok = True
    for name, ok, detail in CHECKS:
        icon = "✓" if ok else "✗"
        # 텔레그램 미설정은 경고로만 처리
        is_warn = not ok and "텔레그램" in name
        status = "WARN" if is_warn else ("OK  " if ok else "FAIL")
        print(f"  [{status}] {icon} {name}: {detail}")
        if not ok and not is_warn:
            all_ok = False

    print("────────────────────────────────────────────────────")
    print("결과:", "ALL PASS" if all_ok else "FAIL — 위 항목 확인 필요")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
