# CLEANUP DESIGN

## 목적

`data-retention.md`에서 정의한 보존 정책을 실제 cleanup 작업으로 구현하기 위한 설계 기준을 정리한다.

이 문서는 retention 정책 자체를 정의하는 문서가 아니라,  
그 정책을 코드와 운영 작업으로 옮기기 위한 **구현 설계 문서**이다.

현재 cleanup job은 아직 구현되지 않았으며,  
이 문서는 향후 `cleanup_job.py` 구현의 기준으로 사용한다.

---

## 설계 목표

cleanup 기능은 아래 목표를 만족해야 한다.

1. 오래된 데이터를 자동으로 정리할 수 있어야 한다
2. 삭제 전 영향 범위를 미리 확인할 수 있어야 한다
3. 기존 job 구조와 일관된 방식으로 구현되어야 한다
4. 운영 결과를 로그와 job_metrics로 추적할 수 있어야 한다
5. 초기 구현은 단순하고 보수적으로 시작해야 한다

---

## 구현 위치

cleanup 작업은 app 내부 job으로 구현한다.

### 대상 파일
- `app/jobs/cleanup_job.py`

### 선택 이유
- 기존 `collect_job.py`, `briefing_job.py`와 동일한 구조를 유지할 수 있다
- cleanup 실행 결과를 `job_metrics`에 기록하기 쉽다
- cron과 연결하기 용이하다
- 운영 경로를 통일할 수 있다

---

## cleanup 대상

현재 cleanup 대상은 아래 두 가지다.

### 1. news_articles
- 기준 컬럼: `collected_at`
- 보존 기간: `90일`
- 정리 대상: 기준 시각보다 오래된 기사 데이터
- 관련 테이블: `article_symbols`
- 처리 방향: `news_articles` 삭제 시 연관 데이터도 함께 정리되도록 설계

### 2. job_metrics
- 기준 컬럼: `started_at`
- 보존 기간: `30일`
- 정리 대상: 기준 시각보다 오래된 운영 로그 데이터

---

## cleanup 비대상

현재 단계에서는 아래 항목은 별도 cleanup 대상으로 다루지 않는다.

### article_symbols
- 독립 cleanup 대상이 아님
- `news_articles` 정리와 함께 처리되는 방향을 전제로 한다

---

## 실행 방식

cleanup은 수동 SQL 실행이 아니라  
**job 실행 방식**으로 동작해야 한다.

예상 실행 예시:

```bash
python -m app.jobs.cleanup_job --dry-run --target all
python -m app.jobs.cleanup_job --target articles
python -m app.jobs.cleanup_job --target metrics