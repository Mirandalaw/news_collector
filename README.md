# news_collector

RSS 뉴스 수집 → 중복 제거 → PostgreSQL 저장 → 아침 브리핑·투자 시그널 생성 → 텔레그램 전송 자동화.
같은 파이프라인 위에 **농산물 가격예측 트랙**(농업 전문지 수집 → 5품목 수급 사건 → 피처 CSV)이 얹혀 있다.

---

## 목차

1. [아키텍처](#아키텍처)
2. [로컬 실행 (빠른 시작)](#로컬-실행-빠른-시작)
3. [Docker 실행](#docker-실행)
4. [농산물 가격예측 트랙](#농산물-가격예측-트랙)
5. [cron 스케줄링](#cron-스케줄링)
6. [환경변수 레퍼런스](#환경변수-레퍼런스)
7. [스모크 테스트](#스모크-테스트)
8. [테스트 실행](#테스트-실행)
9. [운영 체크리스트](#운영-체크리스트)

---

## 아키텍처

```
경제 RSS (10개) ─┐
                 ├─▶ RSSCollector ─▶ NewsIngestionService ─▶ PostgreSQL
농업 RSS (3개)  ─┘        분류(keyword) · 종목/품목 태깅          │
                                                    ┌─────────────┴─────────────┐
                                             BriefingService                 agri_features
                                        (요약 · 투자 시그널 규칙)        (5품목 태깅 · 수급 사건 규칙
                                                    │                       · 클러스터링 · 수량 추출)
                                          BriefingDispatcher                        │
                                           ├─ ConsolePublisher            output/agri_signals.csv
                                           ├─ FilePublisher                (→ price-forecast 입력)
                                           └─ TelegramPublisher
```

**핵심 레이어:**

| 레이어 | 위치 | 역할 |
|--------|------|------|
| Job | `app/jobs/` | cron 진입점, 로깅, 종료코드, job_metrics 기록, cleanup |
| Collector / Parser | `app/collectors/`, `app/parsers/` | RSS 수집, 날짜 정규화 |
| Classifier / Tagger | `app/classifiers/`, `app/taggers/`, `app/sources/` | 기사 분류(company/general/market), 종목·품목 태깅, watchlist |
| Service | `app/services/` | 수집·브리핑 비즈니스 로직 |
| Briefing | `app/briefing/`, `app/summarizers/` | 브리핑 모델/빌더/렌더러, 요약 |
| Signals | `app/signals/` | 규칙 기반 시그널 엔진 (`rules/market_rules`, `symbol_rules`, `event_rules`, **`agri_rules`**), 점수·시뮬레이션, **`agri_features`** |
| Publisher | `app/publishers/` | 전송 채널 추상화 |
| DB | `app/db/`, `docker/initdb/` | PostgreSQL 연결/저장소, 초기 스키마 SQL |

**진입점 (`scripts/`):**

| 스크립트 | 역할 |
|---------|------|
| `run_collect.py` | 경제 RSS 수집 → DB |
| `run_briefing.py` | 브리핑 생성 (`--telegram`, `--save`, `--mock`) |
| `run_all.py` | 수집 → 브리핑 순차 실행 |
| `run_signals.py` | 투자 시그널 분석 (`--hours`, `--no-symbols`, `--fmt json`) |
| `run_review.py` | 브리핑 품질 검수 리포트 |
| `run_metrics.py` | job 실행 메트릭 조회 (`--stats --days 7`) |
| `run_agri_collect.py` | 농업 RSS 수집 + 5품목 태깅 (`--dump DIR` 스냅샷) |
| `run_agri_signals.py` | 농업 기사 → 일자·품목 피처 CSV (`--from-db` / `--from-snapshots`) |
| `smoke_test.py` | 배포 후 기본 동작 확인 |
| `app/jobs/cleanup_job.py` | 보존기간 초과 데이터 삭제 (`--dry-run --target all`) |

---

## 로컬 실행 (빠른 시작)

### 사전 조건

- Python 3.12+
- PostgreSQL 16 (로컬 또는 Docker)

### 설치

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # DB_* 및 TELEGRAM_* 값 입력
```

### DB 초기화

```bash
createdb news_collector
psql news_collector -f docker/initdb/01_schema.sql
```

(또는 첫 수집 실행 시 `app.db.schema.create_tables` 가 테이블을 자동 생성한다.)

### 수동 실행

```bash
python scripts/run_collect.py                                  # 경제 뉴스 수집만
python scripts/run_briefing.py                                 # 브리핑 생성 (콘솔)
python scripts/run_briefing.py --telegram --no-console         # 브리핑 + 텔레그램
python scripts/run_all.py --telegram --no-console              # 수집 → 브리핑
python scripts/run_briefing.py --mock --save --save-fmt json   # AI 없이 모의 요약 + 파일 저장
python scripts/run_signals.py --hours 24 --fmt json --save     # 투자 시그널
python scripts/run_metrics.py --stats --days 7                 # job 메트릭
```

---

## Docker 실행

이미지는 하나(`news-collector:latest`)이고, 서비스마다 실행 명령만 다르다.
배치 서비스는 모두 **`jobs` 프로필**, 유틸리티는 **`tools` 프로필**에 있으므로 `up -d` 로는 뜨지 않고
`run --rm` 으로 한 번씩 실행한다. (`app` 이라는 서비스는 없다.)

| 서비스 | 프로필 | 실행 내용 | 마운트 |
|--------|--------|----------|--------|
| `db` | (항상) | PostgreSQL 16, `127.0.0.1:5432` 만 노출, 빈 볼륨이면 `docker/initdb` 로 스키마 생성 | `pgdata` |
| `collect` | jobs | `run_collect.py` | logs |
| `briefing` | jobs | `run_briefing.py --telegram --no-console` | logs, output |
| `all` | jobs | `run_all.py --telegram --no-console` | logs, output |
| `agri` | jobs | `run_agri_collect.py --dump output/snapshots` | logs, output |
| `agri-signals` | jobs | `run_agri_signals.py --from-snapshots output/snapshots --out output/agri_signals.csv` (DB 불필요) | output |
| `cleanup` | jobs | `app.jobs.cleanup_job` | logs |
| `smoke` | tools | `smoke_test.py` | — |
| `metrics` | tools | `run_metrics.py --stats` | — |
| `webhook` | (항상) | GitHub push webhook 서버 `:9000` (`.env.webhook` 필요) | logs |

### 빌드 및 시작

```bash
cp .env.example .env                       # TELEGRAM_* 입력. DB_HOST 는 compose 가 db 로 덮어씀
docker compose up -d db                    # DB 기동 (webhook 도 쓰면 up -d)
docker compose --profile jobs build collect   # 이미지 1회 빌드 (코드 바뀔 때마다 다시)
docker compose --profile tools run --rm smoke # 연결 확인
```

### 개별 명령 실행

```bash
docker compose --profile jobs run --rm collect
docker compose --profile jobs run --rm briefing
docker compose --profile jobs run --rm all
docker compose --profile jobs run --rm cleanup --dry-run --target all
docker compose --profile tools run --rm metrics

# 서비스에 없는 스크립트는 briefing 서비스(logs+output 마운트)에 명령을 덮어써서 실행
docker compose --profile jobs run --rm briefing python scripts/run_signals.py --hours 24
docker compose logs -f db
```

### 볼륨 구조

```
./logs/     ← /app/logs    (job 로그: collect_YYYYMMDD.log, agri_collect_YYYYMMDD.log …)
./output/   ← /app/output  (브리핑 파일, snapshots/*.jsonl, agri_signals.csv)
pgdata      ← Docker named volume (DB 데이터)
```

---

## 농산물 가격예측 트랙

2026 AI 농산물 가격예측 해커톤(배추·무·양파·깐마늘·건고추)용. 경제 브리핑과 독립이며 `category="농업"` 으로 구분된다.
`cleanup_job` 은 농업 기사를 보존기간 삭제 대상에서 제외한다 (백테스트·재현 검증 코퍼스).

```
농업 RSS 3개 ─▶ 수집·저장 ─▶ AgriTagger (5품목) ─▶ 스냅샷 jsonl
   (한국농어민신문·농수축산신문·농축유통신문)              │
                                                         ▼
                 agri_features: 사건 클러스터링 → AGRI_RULES 14종 → 수량 추출 → (date, item) 집계
                                                         │
                                                         ▼
                                              output/agri_signals.csv
```

### 실행

```bash
docker compose --profile jobs run --rm agri              # 수집 + output/snapshots/<날짜>.jsonl
docker compose --profile jobs run --rm agri-signals      # 스냅샷 → output/agri_signals.csv

# 로컬 (venv)
python scripts/run_agri_collect.py --dump output/snapshots
python scripts/run_agri_signals.py --from-snapshots output/snapshots --out output/agri_signals.csv
python scripts/run_agri_signals.py --from-db --since 2026-01-01 --out output/agri_signals.csv
```

`output/agri_signals.csv` 를 [price-forecast](https://github.com/Mirandalaw/price-forecast) 의 `data/` 로 복사하면 뉴스 피처로 학습된다.

### 구성 요소

| 파일 | 내용 |
|------|------|
| `app/sources/agri_sources.py` | 농업 RSS 소스 (`AGRI_SOURCES`), 미확인 소스 메모 |
| `app/sources/agri_watchlist.py` | 5품목 키워드 watchlist, veto 키워드, **`AgriTagger`** |
| `app/signals/rules/agri_rules.py` | 수급 사건 규칙 14종 (`AGRI_RULES`), 사후보도 veto, 중요도 가중 |
| `app/signals/agri_features.py` | 스냅샷/DB 읽기 → 태깅 → 클러스터링 → 규칙 평가 → 집계 → CSV (표준 라이브러리만 사용) |
| `scripts/run_agri_collect.py`, `scripts/run_agri_signals.py` | 진입점 |
| `tests/test_agri_rules.py`, `tests/test_agri_features.py` | 단위 테스트 |

**품목 태깅 (`AgriTagger`)** — 제목에 품목 키워드가 있으면 태깅, 없으면 요약에 키워드가 2회 이상일 때만 태깅.
요리·가공식품 문맥(`AGRI_VETO_KEYWORDS`)은 제외. "무"처럼 짧은 단어는 복합어(가을무·김장무·무 가격 …)만 쓴다.

**수급 사건 규칙 (`AGRI_RULES`)** — 방향은 `BULLISH = 공급 감소(+1)`, `BEARISH = 공급 증가·수요 감소(−1)`.

| 구분 | 규칙 | 방향 | 지평 |
|------|------|------|------|
| 공급 감소 | 태풍 · 폭우 · 폭염/가뭄 · 냉해 · 병해충 · 재배면적 감소 · 출하 지연 · 정부 수매/시장격리 | +1 | 단기/중기 |
| 공급 증가 | 비축 방출 · TRQ/할당관세 수입(양파·깐마늘·건고추) · 작황 양호 · 출하 본격화 · 할인/수급 대책 | −1 | 단기/중기 |
| 수요 증가 | 김장 수요 | +1 | 중기 (가중 0.5) |

"금배추"·"폭등"·"한 포기에" 같은 사후 보도 표현이 있으면 모든 규칙에서 발동 취소 (`POSTHOC_VETO`).
기사 속 가격 숫자(원)는 일부러 추출하지 않는다 — 미래 가격이 피처로 새는 경로이기 때문.

**출력 CSV 컬럼** (`date, item` 조합당 1행, 기사가 있는 날만):

| 컬럼 | 의미 |
|------|------|
| `news_cnt` | 그날 해당 품목 태깅 기사 수 |
| `event_cnt`, `dir_sum` | 사건(클러스터) 수, 방향 합 |
| `dir_wsum` | 방향 × 중요도(HIGH 1.0 / MEDIUM 0.8 / LOW 0.5) × 매체 수(≤1.5) × 숫자 없으면 0.5 |
| `evt_<rule>` | 규칙별 발동 횟수 (14개) |
| `mag_ton`, `mag_pct` | 기사에서 뽑은 톤 · % 수량 (`1만5000톤` 식 '만' 단위 처리) |
| `macro_fx_up`, `macro_oil_up` | 그날 경제 기사의 달러 강세·유가 급등 규칙 발동 수 (전 품목 공통) |

### 재현 검증 (폐쇄망)

`output/snapshots/YYYY-MM-DD.jsonl` 이 원본이다. `agri-signals` 는 DB·외부 API 없이 이 파일만 읽고,
`agri_features.py` 는 pandas 없이 표준 라이브러리만으로 동작하므로 스냅샷 폴더와 함께 제출하면 그대로 재현된다.

---

## cron 스케줄링

`crontab.example` 을 참고해 `crontab -e` 로 등록한다. (cron 은 PATH 가 제한되므로 절대경로 사용)

```bash
# venv 직접 실행
0  6 * * *  /path/.venv/bin/python /path/scripts/run_collect.py
10 6 * * *  /path/.venv/bin/python /path/scripts/run_briefing.py --telegram --no-console

# Docker (서버 운영 방식)
0 21 * * *   cd /home/kdpark/news_collector && docker compose --profile jobs run --rm collect  >> logs/collect_cron.log 2>&1
10 21 * * *  cd /home/kdpark/news_collector && docker compose --profile jobs run --rm briefing >> logs/briefing_cron.log 2>&1
0 9,16 * * * cd /home/kdpark/news_collector && docker compose --profile jobs run --rm agri    >> logs/agri_cron.log 2>&1
0 3 * * 0    cd /home/kdpark/news_collector && docker compose --profile jobs run --rm cleanup --target all >> logs/cleanup_cron.log 2>&1
```

농업 피드는 보도자료·산지 기사가 오전·오후로 나뉘어 올라오므로 하루 2회 수집한다.

---

## 환경변수 레퍼런스

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_HOST` | `localhost` | PostgreSQL 호스트 (compose 에서는 `db` 로 고정) |
| `DB_PORT` | `5432` | PostgreSQL 포트 |
| `DB_NAME` | `news_collector` | DB 이름 |
| `DB_USER` | `news` | DB 사용자 |
| `DB_PASSWORD` | `changeme` | DB 비밀번호 (운영에서는 반드시 변경) |
| `TELEGRAM_BOT_TOKEN` | — | BotFather 발급 토큰 (브리핑 전송 시 필수) |
| `TELEGRAM_CHAT_ID` | — | 수신 채팅 ID (브리핑 전송 시 필수) |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LOG_DIR` | `logs` | 로그 파일 저장 디렉토리 |
| `BRIEFING_HOURS_BACK` | `12` | 브리핑·시그널 조회 시간 범위 |
| `BRIEFING_OUTPUT_DIR` | `output` | 브리핑·시그널 파일 저장 디렉토리 |
| `WEBHOOK_SECRET` | — | GitHub webhook secret (`.env.webhook`, webhook 서비스만) |

> 토큰·비밀번호는 `.env` 에만 둔다. `crontab.example` 같은 커밋되는 파일에는 자리표시자만 남길 것.

---

## 스모크 테스트

```bash
python scripts/smoke_test.py                       # 로컬
docker compose --profile tools run --rm smoke      # Docker
```

| 항목 | 실패 시 조치 |
|------|-------------|
| DB 연결 | DB_* 환경변수 확인, PostgreSQL 기동 확인 |
| 테이블 존재 | `docker/initdb/01_schema.sql` 적용 또는 `create_tables` 실행 |
| 모듈 임포트 | `pip install -r requirements.txt` |
| 텔레그램 설정 | TELEGRAM_* 입력 (경고만, 실패 아님) |

---

## 테스트 실행

```bash
pytest -m "not integration"                                   # 유닛 테스트 (DB 불필요)
pytest -m integration                                         # 통합 테스트 (실제 DB 필요)
pytest -m "not integration" --cov=app --cov-report=term-missing
pytest tests/test_agri_rules.py tests/test_agri_features.py   # 농산물 트랙만
ruff check . && ruff format --check .                         # CI 와 동일 (ruff 0.11.5)
```

CI (GitHub Actions) 는 PR 마다 `Lint (ruff)` 와 `Unit Tests` 를 실행한다.

---

## 운영 체크리스트

### 초기 배포

- [ ] `.env` 작성 (DB_PASSWORD 변경, TELEGRAM_* 입력)
- [ ] `docker compose up -d db` → `--profile tools run --rm smoke` 통과
- [ ] 이미지 빌드 `--profile jobs build collect`
- [ ] 텔레그램 봇 테스트 메시지 수신 확인
- [ ] cron 등록 (경제 수집·브리핑, 농업 수집 2회, cleanup 주 1회)

### 정기 점검

- [ ] `logs/` 용량 확인, `output/snapshots/` 날짜별 파일 생성 확인
- [ ] `docker compose --profile tools run --rm metrics` 로 job 성공률 확인
- [ ] 농업 태깅 건수 확인: `logs/agri_collect_YYYYMMDD.log` 의 `품목태깅=N` (0이 이어지면 피드·키워드 점검)
- [ ] DB 용량 확인 (`SELECT category, COUNT(*) FROM news_articles GROUP BY 1`)

### 이슈 대응

| 증상 | 확인 방법 |
|------|----------|
| `no such service: app` | 서비스명은 `collect`/`briefing`/`all`/`agri` 등이며 `--profile jobs` 필요 |
| 브리핑 미발송 | `logs/briefing_YYYYMMDD.log` |
| 수집 0건 | RSS URL 접근 가능 여부, `logs/collect_*.log` / `logs/agri_collect_*.log` |
| 품목 태깅 오탐 | `app/sources/agri_watchlist.py` 키워드·veto 조정 후 `agri-signals` 재실행 (스냅샷은 재태깅됨) |
| `agri_signals.csv` 사건 0건 | 정상일 수 있음 (수급 사건 기사가 없는 날). 규칙 트리거는 `agri_rules.py` |
| DB 연결 실패 | `python scripts/smoke_test.py` |
| 텔레그램 미수신 | 봇 토큰 유효성, 채팅 ID 확인 |
