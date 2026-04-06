# RUNBOOK — news_collector 운영 런북

> 운영 환경: Beelink 서버 · Docker Compose · PostgreSQL 16

---

## 빠른 참조

```bash
# DB 시작
docker compose up -d db

# 수집 실행
docker compose run --rm --profile jobs collect

# 브리핑 실행
docker compose run --rm --profile jobs briefing

# 스모크 테스트
docker compose run --rm --profile tools smoke

# 전체 상태 확인
docker compose ps
```

---

## 서비스 실행

### 초기 시작 (최초 배포 or 재설치)

```bash
cd ~/news_collector

# .env 설정 확인
cat .env | grep -v '^#' | grep -v '^$'

# 이미지 빌드
docker compose build

# DB 시작 + 헬스체크 대기
docker compose up -d db
docker compose ps   # db 상태가 healthy 될 때까지 대기 (최대 1~2분)

# 스모크 테스트 (DB 연결 + 기본 동작 확인)
docker compose run --rm --profile tools smoke

# 첫 수집 실행
docker compose run --rm --profile jobs collect
```

### 일반 실행 (cron에서 자동 호출)

```bash
# 수집만
docker compose run --rm --profile jobs collect

# 브리핑만
docker compose run --rm --profile jobs briefing

# 수집 + 브리핑 순차 실행
docker compose run --rm --profile jobs all
```

### DB만 재시작

```bash
docker compose restart db
# 헬스체크 통과 확인
docker compose ps
```

---

## 로그 확인

### 컨테이너 실행 로그 (최근)

```bash
# DB 로그
docker compose logs db --tail 30

# 마지막으로 실행한 job 로그 (--rm 컨테이너는 종료 후 사라짐)
# → 파일 로그를 확인할 것
```

### 파일 로그 (logs/ 디렉토리)

```bash
# 오늘 수집 로그
tail -50 logs/collect_$(date +%Y%m%d).log

# 오늘 브리핑 로그
tail -50 logs/briefing_$(date +%Y%m%d).log

# 오늘 전체 실행 로그
tail -50 logs/all_$(date +%Y%m%d).log

# 실시간 확인 (job 실행 중)
tail -f logs/collect_$(date +%Y%m%d).log
```

### job 메트릭 (성공/실패 이력)

```bash
docker compose run --rm --profile tools metrics
```

---

## 장애 대응

### 브리핑이 텔레그램에 안 왔을 때

```bash
# 1. 브리핑 로그 확인
tail -50 logs/briefing_$(date +%Y%m%d).log

# 2. 텔레그램 설정 확인
grep TELEGRAM .env

# 3. 수집된 기사 수 확인 (0건이면 수집 실패)
docker compose run --rm --profile tools metrics

# 4. 수동 재실행
docker compose run --rm --profile jobs briefing
```

**원인별 조치**

| 로그 메시지 | 조치 |
|---|---|
| `TELEGRAM_BOT_TOKEN 미설정` | `.env`에 토큰 추가 후 재실행 |
| `HTTPError 401` | BotFather에서 `/revoke` 후 새 토큰 발급 |
| `기사 0건` | 아래 "수집 0건" 항목 확인 |
| `DB 연결 실패` | 아래 "DB 연결 문제" 항목 확인 |

---

### 수집 0건일 때

```bash
# 1. 수집 로그 확인
tail -100 logs/collect_$(date +%Y%m%d).log

# 2. DB 연결 확인
docker compose run --rm --profile tools smoke

# 3. RSS 피드 접근 테스트 (서버에서 직접)
curl -I "https://feeds.yna.co.kr/economy.xml"

# 4. 수동 재실행
docker compose run --rm --profile jobs collect
```

**원인별 조치**

| 증상 | 조치 |
|---|---|
| DB 연결 오류 | 아래 "DB 연결 문제" 항목 확인 |
| `curl` 응답 없음 | 서버 네트워크 또는 DNS 확인 |
| 특정 소스만 0건 | 해당 RSS URL 변경 여부 확인 |

---

### DB 연결 문제

```bash
# 1. 컨테이너 상태 확인
docker compose ps

# 2. DB 로그 확인
docker compose logs db --tail 30

# 3. DB 재시작
docker compose restart db

# 4. 재시작 후 헬스체크 대기 (~30초)
docker compose ps   # db healthy 확인

# 5. 연결 재테스트
docker compose run --rm --profile tools smoke
```

**DB 컨테이너가 계속 unhealthy일 때**

```bash
# 볼륨 권한 확인
docker volume inspect news_collector_pgdata

# 강제 재생성 (데이터 유지)
docker compose stop db
docker compose up -d db

# 최후 수단 — 데이터 초기화 (운영 데이터 삭제됨, 반드시 백업 먼저)
# docker compose down -v
# docker compose up -d db
```

**`.env` 비밀번호 불일치 확인**

```bash
# .env 값과 컨테이너 환경변수 비교
grep DB_PASSWORD .env
docker compose exec db env | grep POSTGRES_PASSWORD
```

---

### 컨테이너 재시작

```bash
# DB만 재시작
docker compose restart db

# 이미지 재빌드 후 반영 (코드 변경 시)
docker compose build
# → 다음 cron 실행 시 새 이미지 자동 사용

# 전체 정리 후 재시작 (DB 데이터는 유지됨)
docker compose down
docker compose up -d db
```

---

## 환경변수 수정

```bash
# 1. .env 파일 편집
vi ~/.news_collector/.env   # 또는 ~/news_collector/.env

# 2. 변경 확인
cat .env | grep -v '^#' | grep -v '^$'

# 3. DB 컨테이너는 재시작 필요 (POSTGRES_* 변수 변경 시)
docker compose restart db

# 4. app 서비스는 재시작 불필요
# docker compose run --rm --profile jobs collect 실행 시 .env 자동 로딩
```

**주요 환경변수**

| 변수 | 설명 |
|---|---|
| `DB_PASSWORD` | PostgreSQL 비밀번호 (DB 재시작 필요) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 전송 대상 채팅 ID |
| `BRIEFING_HOURS_BACK` | 브리핑에 포함할 시간 범위 (기본: 12) |
| `LOG_LEVEL` | 로그 레벨 (DEBUG / INFO / WARNING) |

---

## DB 관리

### 백업

```bash
# 백업 생성
docker compose exec db \
    pg_dump -U ${DB_USER:-news} ${DB_NAME:-news_collector} \
    > backup_$(date +%Y%m%d).sql

echo "백업 완료: backup_$(date +%Y%m%d).sql"
```

### 복원

```bash
# 복원 전 반드시 DB 컨테이너가 running 상태여야 함
docker compose exec -T db \
    psql -U ${DB_USER:-news} ${DB_NAME:-news_collector} \
    < backup_20260405.sql
```

### 오래된 데이터 정리

```bash
# 90일 이전 기사 삭제
docker compose run --rm --profile tools smoke   # 먼저 연결 확인

docker compose exec db psql -U ${DB_USER:-news} ${DB_NAME:-news_collector} -c "
    DELETE FROM news_articles
    WHERE collected_at < NOW() - INTERVAL '90 days';
"

# job_metrics 180일 이전 정리
docker compose exec db psql -U ${DB_USER:-news} ${DB_NAME:-news_collector} -c "
    DELETE FROM job_metrics
    WHERE started_at < NOW() - INTERVAL '180 days';
"
```

### DB 용량 확인

```bash
docker compose exec db psql -U ${DB_USER:-news} ${DB_NAME:-news_collector} -c "
    SELECT
        relname AS table,
        pg_size_pretty(pg_total_relation_size(relid)) AS size
    FROM pg_catalog.pg_statio_user_tables
    ORDER BY pg_total_relation_size(relid) DESC;
"
```

---

## 재배포 (코드 업데이트)

```bash
cd ~/news_collector

# 1. 코드 업데이트
git pull

# 2. 이미지 재빌드
docker compose build

# 3. 스모크 테스트
docker compose run --rm --profile tools smoke

# 4. 수동 실행으로 검증
docker compose run --rm --profile jobs collect
```

---

## 운영 체크리스트

### 매일
- [ ] 텔레그램에 브리핑 수신 확인
- [ ] `docker compose ps` — db healthy 상태 확인

### 주간
- [ ] `docker compose run --rm --profile tools metrics` — 7일 성공률 확인
- [ ] `du -sh logs/` — 로그 크기 확인

### 월간
- [ ] DB 백업 (`pg_dump`)
- [ ] 오래된 로그 정리: `find logs/ -name "*.log" -mtime +30 -delete`
- [ ] `docker compose build --no-cache` — 베이스 이미지 업데이트
