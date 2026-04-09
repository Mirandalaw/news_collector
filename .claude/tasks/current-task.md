# CURRENT TASK

## 작업명
cleanup job 기본 구조 생성

## 목표
retention 정책에 따라 오래된 데이터를 정리할 수 있는 cleanup job의 기본 실행 구조를 만든다.

현재 단계에서는 실제 삭제 로직 전체를 한 번에 구현하지 않고,  
기존 job 패턴에 맞는 cleanup job의 뼈대와 실행 흐름을 먼저 만든다.

---

## 현재 상태

- 뉴스 수집 및 브리핑 시스템의 MVP는 구현 완료 상태다
- event 섹션은 구현 및 1차 보정이 완료되었고 관찰 단계다
- retention 정책은 `data-retention.md`에 정의되어 있다
- cleanup 구현 설계는 `cleanup-design.md`에 정리되어 있다
- 현재 `cleanup_job.py`는 아직 존재하지 않는다

즉, 현재 단계는  
**cleanup 기능의 실제 구현을 시작하기 전, 기본 구조를 만드는 단계**이다.

---

## 이번 단계에서 해야 할 일

1. `app/jobs/cleanup_job.py` 파일 생성
2. 기존 `collect_job.py`, `briefing_job.py`와 동일한 job 패턴 사용
3. CLI 인자 구조 추가
   - `--dry-run`
   - `--target articles|metrics|all`
4. 함수 뼈대 작성
   - `cleanup_articles(dry_run: bool)`
   - `cleanup_metrics(dry_run: bool)`
   - `main()`
5. `setup_job_logging`, `JobResult`, `try_record_job_run` 패턴 연결
6. target에 따라 articles / metrics / all 분기되는 실행 흐름 구성

---

## 이번 단계에서 하지 말아야 할 일

아래 작업은 이번 단계의 범위가 아니다.

- 실제 DELETE SQL 구현
- archive 기능 추가
- config/env 외부화
- 다른 job 파일 리팩토링
- builder / renderer / classifier 수정
- cleanup 통계 고도화
- 관리자용 기능 추가

---

## 이번 단계의 설계 원칙

1. 기존 job 구조를 그대로 따른다
2. 작은 변경으로 시작한다
3. 실행 가능한 뼈대를 먼저 만든다
4. 다음 단계에서 dry-run과 delete를 붙일 수 있는 형태로 만든다
5. 과한 추상화 없이 명확한 함수 구조를 유지한다

---

## 완료 조건

아래 조건을 만족하면 이번 단계는 완료다.

1. `cleanup_job.py` 파일이 생성되어 있다
2. CLI 인자 파싱이 동작한다
3. `--target` 값에 따라 분기된다
4. `cleanup_articles`, `cleanup_metrics`, `main` 구조가 존재한다
5. logging / JobResult / try_record_job_run 패턴이 기존 job과 일관된다
6. 다음 단계에서 dry-run 로직만 붙이면 될 상태다

---

## 다음 단계

이번 단계 완료 후 다음 순서로 진행한다.

1. dry-run 구현
2. articles 대상 건수 조회
3. metrics 대상 건수 조회
4. 실제 batch delete 구현
5. 수동 실행 검증
6. cron 등록

---

## 참고 문서

이번 작업에서는 아래 문서를 반드시 따른다.

- `project-overview.md`
- `data-retention.md`
- `cleanup-design.md`
- `constraints.md`
- `output-format.md`

---

## 작업 판단 기준

이번 단계의 좋은 결과는 아래와 같다.

- cleanup job이 기존 구조와 자연스럽게 맞물린다
- 다음 단계 구현이 쉽게 이어진다
- 변경 범위가 작고 명확하다
- 불필요한 기능이 추가되지 않는다