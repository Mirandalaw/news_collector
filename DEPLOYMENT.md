# DEPLOYMENT.md — Beelink 서버 배포 가이드

## 전제 조건

| 항목 | 요구사항 |
|------|----------|
| OS | Ubuntu 22.04 LTS (권장) |
| Python | 3.12+ |
| Docker | 24.0+ |
| Docker Compose | v2.20+ |
| 네트워크 | 인터넷 접속 가능 (RSS 수집, 텔레그램 전송) |

---

## 1. 서버 초기 설정

```bash
# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지
sudo apt install -y python3.12 python3.12-venv python3-pip git curl

# Docker 설치 (공식 스크립트)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 재로그인 후 docker ps 로 확인
```

---

## 2. 프로젝트 배포

```bash
# 1. 프로젝트 클론 (또는 scp로 복사)
cd ~
git clone <repo-url> news_collector
cd news_collector

# 2. Python 가상환경 생성
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
nano .env     # 실제 값 입력
```

### .env 필수 값

```bash
# DB (Docker compose의 postgres 컨테이너와 일치시킬 것)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_collector
DB_USER=news
DB_PASSWORD=<강력한_패스워드>

# 텔레그램
TELEGRAM_BOT_TOKEN=<BotFather_발급_토큰>
TELEGRAM_CHAT_ID=<본인_채팅_ID>

# 로그
LOG_LEVEL=INFO
LOG_DIR=/opt/news-collector/logs
BRIEFING_OUTPUT_DIR=/opt/news-collector/output
```

---

## 3. PostgreSQL 시작 (Docker)

```bash
# DB 컨테이너만 시작 (앱은 호스트에서 직접 실행)
docker compose up -d db

# 헬스체크 확인 (healthy 상태 대기)
docker compose ps

# DB 스키마 초기화
source .venv/bin/activate
python - <<'EOF'
from app.db.connection import DatabaseConfig, get_connection
from app.db.schema import create_tables
conn = get_connection(DatabaseConfig.from_env())
create_tables(conn)
conn.commit()
conn.close()
print("스키마 초기화 완료")
EOF
```

---

## 4. 스모크 테스트

```bash
# 기본 동작 확인 (DB 연결, 테이블, 임포트)
python scripts/smoke_test.py

# 수집 테스트 (실제 RSS 요청)
python scripts/run_collect.py

# 브리핑 테스트 (콘솔 출력)
python scripts/run_briefing.py --mock

# 텔레그램 테스트
python scripts/run_briefing.py --mock --telegram
```

---

## 5. 스케줄링 설정

### 방법 A: systemd timer (권장 — Beelink)

```bash
# 서비스 파일 복사
sudo cp systemd/news-collect.service  /etc/systemd/system/
sudo cp systemd/news-collect.timer    /etc/systemd/system/
sudo cp systemd/news-briefing.service /etc/systemd/system/
sudo cp systemd/news-briefing.timer   /etc/systemd/system/

# 경로 수정 (kdpark → 실제 사용자명)
sudo sed -i 's/kdpark/'"$USER"'/g' /etc/systemd/system/news-*.service

# 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable news-collect.timer news-briefing.timer
sudo systemctl start  news-collect.timer news-briefing.timer

# 상태 확인
systemctl list-timers news-*
```

### 방법 B: crontab

```bash
crontab -e
```

`crontab.example` 내용 참고:
```cron
PROJ=/opt/news-collector
VENV=$PROJ/.venv/bin/python

# 매일 KST 06:00 수집
0  21 * * *  $VENV $PROJ/scripts/run_collect.py

# 매일 KST 06:10 브리핑
10 21 * * *  $VENV $PROJ/scripts/run_briefing.py --telegram --no-console
```

---

## 6. Docker 전체 실행 (선택)

DB + 앱을 모두 Docker로 실행하고 싶다면:

```bash
# 빌드
docker compose build

# DB 시작
docker compose up -d db

# 수동 실행
docker compose --profile jobs run --rm collect
docker compose --profile jobs run --rm briefing

# cron에서 Docker로 실행
# 0 21 * * *  cd /opt/news-collector && docker compose --profile jobs run --rm collect
```

---

## 7. 로그 디렉토리 설정

```bash
mkdir -p ~/news_collector/logs
mkdir -p ~/news_collector/output

# 로그 로테이션 (선택)
sudo tee /etc/logrotate.d/news-collector <<'EOF'
/opt/news-collector/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
EOF
```

---

## 8. 배포 완료 체크리스트

- [ ] `.env` 파일 생성 및 모든 값 입력
- [ ] `python scripts/smoke_test.py` 통과
- [ ] `docker compose ps` — db 서비스 healthy
- [ ] DB 스키마 초기화 완료
- [ ] 수동 수집 테스트 성공 (`run_collect.py`)
- [ ] 수동 브리핑 테스트 성공 (`run_briefing.py --mock`)
- [ ] 텔레그램 수신 확인
- [ ] systemd timer 또는 crontab 등록 완료
- [ ] 로그 디렉토리 생성 및 쓰기 권한 확인
- [ ] `python scripts/run_metrics.py --stats` 정상 실행
