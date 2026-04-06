#!/usr/bin/env bash
# ============================================================
# news_collector job runner
#
# 사용법:
#   ./job.sh collect          # 뉴스 수집
#   ./job.sh briefing         # 브리핑 생성 + 텔레그램 전송
#   ./job.sh all              # 수집 → 브리핑 순차 실행
#   ./job.sh smoke            # 스모크 테스트
#   ./job.sh metrics          # job 실행 메트릭 확인
#
# crontab 등록 예시 (crontab -e):
#   0  21 * * *  /home/kdpark/news_collector/job.sh collect
#  10  21 * * *  /home/kdpark/news_collector/job.sh briefing
# ============================================================

set -euo pipefail

# 이 스크립트가 있는 디렉토리로 이동 (cron 실행 시 경로 문제 방지)
cd "$(dirname "$0")"

JOB="${1:-}"

if [[ -z "$JOB" ]]; then
    echo "사용법: $0 {collect|briefing|all|smoke|metrics}" >&2
    exit 1
fi

case "$JOB" in
    collect|briefing|all)
        exec docker compose --profile jobs run --rm "$JOB"
        ;;
    smoke|metrics)
        exec docker compose --profile tools run --rm "$JOB"
        ;;
    *)
        echo "알 수 없는 job: $JOB" >&2
        echo "사용 가능: collect, briefing, all, smoke, metrics" >&2
        exit 1
        ;;
esac
