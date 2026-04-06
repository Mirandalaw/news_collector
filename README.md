# news_collector

RSS 뉴스 수집 → 중복 제거 → PostgreSQL 저장 → 아침 브리핑 생성 → 텔레그램 전송 자동화 시스템.

---

## 목차

1. [아키텍처](#아키텍처)
2. [로컬 실행 (빠른 시작)](#로컬-실행-빠른-시작)
3. [Docker 실행](#docker-실행)
4. [cron 스케줄링](#cron-스케줄링)
5. [환경변수 레퍼런스](#환경변수-레퍼런스)
6. [스모크 테스트](#스모크-테스트)
7. [테스트 실행](#테스트-실행)
8. [운영 체크리스트](#운영-체크리스트)

---

## 아키텍처

```
RSS 피드
  └─▶ RSSCollector ──▶ NewsIngestionService ──▶ PostgreSQL
                                                    │
                                           BriefingService
                                                    │
                                          MorningBriefingService
                                                    │
                                         BriefingDispatcher
                                          ├─ ConsolePublisher
                                          ├─ FilePublisher
                                          └─ TelegramPublisher
```

**핵심 레이어:**

| 레이어 | 위치 | 역할 |
|--------|------|------|
| Job | `app/jobs/` | cron 진입점, 로깅, 종료코드 |
| Service | `app/services/` | 비즈니스 로직 |
| Briefing | `app/briefing/` | 브리핑 모델/빌더/렌더러 |
| Publisher | `app/publishers/` | 전송 채널 추상화 |
| DB | `app/db/` | PostgreSQL 연결/저장소 |

---

## 로컬 실행 (빠른 시작)

### 사전 조건

- Python 3.12+
- PostgreSQL (로컬 또는 Docker)

### 설치

```bash
# 1. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements-dev.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 DB_* 및 TELEGRAM_* 값 입력
```

### DB 초기화

```bash
# PostgreSQL에 접속해서 DB 생성
createdb news_collector

# 테이블 생성 (Python에서)
python - <<'EOF'
from app.db.connection import DatabaseConfig, get_connection
from app.db.schema import create_tables
conn = get_connection(DatabaseConfig.from_env())
create_tables(conn)
conn.commit()
conn.close()
print("테이블 생성 완료")
EOF
```

### 수동 실행

```bash
# 뉴스 수집만
python scripts/run_collect.py

# 브리핑 생성 (콘솔 출력)
python scripts/run_briefing.py

# 브리핑 + 텔레그램 전송
python scripts/run_briefing.py --telegram --no-console

# 수집 → 브리핑 한 번에
python scripts/run_all.py --telegram --no-console

# 모의 요약(AI 없이) + 파일 저장
python scripts/run_briefing.py --mock --save --save-fmt json
```

---

## Docker 실행

### 빌드 및 시작

```bash
# .env 파일 준비 (DB_HOST는 자동으로 docker-compose가 db로 덮어씀)
cp .env.example .env
# .env 에서 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 입력

# 전체 스택 시작 (postgres + app)
docker compose up -d

# 로그 확인
docker compose logs -f app
```

### 개별 명령 실행

```bash
# 수집만 실행
docker compose run --rm app python scripts/run_collect.py

# 브리핑만 실행
docker compose run --rm app python scripts/run_briefing.py --telegram --no-console

# 스모크 테스트
docker compose --profile tools run --rm smoke
```

### 볼륨 구조

```
./logs/    ← 컨테이너 /app/logs 와 마운트 (로그 파일 보존)
./output/  ← 컨테이너 /app/output 와 마운트 (브리핑 파일 보존)
pgdata     ← Docker named volume (DB 데이터 영구 보존)
```

---

## cron 스케줄링

`crontab.example` 파일을 참고해서 `crontab -e`로 등록하세요.

```bash
# 예시: 매일 오전 6:00 수집 / 6:10 브리핑 전송
0  6 * * *  /path/to/.venv/bin/python /path/to/scripts/run_collect.py
10 6 * * *  /path/to/.venv/bin/python /path/to/scripts/run_briefing.py --telegram --no-console
```

> **주의:** cron은 PATH가 제한됩니다. `crontab.example`처럼 절대경로와 환경변수를 명시하세요.

---

## 환경변수 레퍼런스

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_HOST` | `localhost` | PostgreSQL 호스트 |
| `DB_PORT` | `5432` | PostgreSQL 포트 |
| `DB_NAME` | `news_collector` | DB 이름 |
| `DB_USER` | OS 유저명 | DB 사용자 |
| `DB_PASSWORD` | (빈값) | DB 비밀번호 |
| `TELEGRAM_BOT_TOKEN` | — | BotFather 발급 토큰 (필수) |
| `TELEGRAM_CHAT_ID` | — | 수신 채팅 ID (필수) |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LOG_DIR` | `logs` | 로그 파일 저장 디렉토리 |
| `BRIEFING_HOURS_BACK` | `12` | 브리핑 조회 시간 범위 |
| `BRIEFING_OUTPUT_DIR` | `output` | 브리핑 파일 저장 디렉토리 |

---

## 스모크 테스트

배포 후 또는 환경 변경 후 기본 동작을 확인합니다.

```bash
# 로컬
python scripts/smoke_test.py

# Docker
docker compose --profile tools run --rm smoke
```

**확인 항목:**

| 항목 | 실패 시 조치 |
|------|-------------|
| DB 연결 | DB_* 환경변수 확인, PostgreSQL 기동 확인 |
| 테이블 존재 | DB 초기화 (create_tables) 실행 |
| 모듈 임포트 | 의존성 설치 확인 (pip install -r requirements.txt) |
| 텔레그램 설정 | TELEGRAM_* 환경변수 입력 (경고만, 실패 아님) |

---

## 테스트 실행

```bash
# 유닛 테스트 (DB 불필요)
pytest -m "not integration"

# 통합 테스트 (실제 DB 필요)
pytest -m integration

# 커버리지 포함
pytest -m "not integration" --cov=app --cov-report=term-missing
```

---

## 운영 체크리스트

### 초기 배포

- [ ] `.env` 파일 생성 및 모든 환경변수 입력
- [ ] `python scripts/smoke_test.py` 통과 확인
- [ ] DB 스키마 초기화 완료 (테이블 존재 확인)
- [ ] 텔레그램 봇 테스트 메시지 수신 확인

### 정기 점검

- [ ] `logs/` 디렉토리 파일 크기 확인 (오래된 로그 삭제)
- [ ] `output/` 디렉토리 브리핑 파일 생성 확인
- [ ] DB 용량 확인 (`SELECT COUNT(*) FROM news_articles`)
- [ ] cron 실행 이력 확인 (`grep CRON /var/log/syslog`)

### 이슈 대응

| 증상 | 확인 방법 |
|------|----------|
| 브리핑 미발송 | `logs/briefing_YYYYMMDD.log` 확인 |
| 수집 0건 | RSS URL 접근 가능 여부 확인, `logs/collect_*.log` 확인 |
| DB 연결 실패 | `python scripts/smoke_test.py` 실행 |
| 텔레그램 미수신 | 봇 토큰 유효성, 채팅 ID 확인 |
