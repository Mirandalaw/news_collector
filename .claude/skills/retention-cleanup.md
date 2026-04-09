# SKILL: retention-cleanup

## ROLE

너는 cleanup 및 데이터 보존 정책을 구현하는 코드 에이전트다.

항상 다음 문서를 기준으로 작업한다.

- `project-overview.md`
- `data-retention.md`
- `cleanup-design.md`
- `constraints.md`
- `current-task.md`
- `output-format.md`

---

## INPUT

- retention 정책 (`data-retention.md`)
- cleanup 설계 (`cleanup-design.md`)
- 현재 작업 범위 (`current-task.md`)
- 기존 job 구조 (`collect_job.py`, `briefing_job.py`)

---

## TASK

cleanup 관련 기능을 단계적으로 구현한다.

현재 단계에서 요구된 작업만 수행하며,  
다음 단계의 기능을 미리 구현하지 않는다.

---

## WORKFLOW

cleanup 작업은 아래 순서로 진행한다.

1. 기본 구조 생성
2. dry-run 구현
3. articles cleanup 구현
4. metrics cleanup 구현
5. batch delete 적용
6. 실행 결과 기록
7. 수동 검증
8. cron 연결

각 단계는 독립적으로 수행한다.

---

## RULES

### 1. 단계별 구현 원칙
- 한 번에 한 단계만 구현한다
- 현재 단계 요구사항만 반영한다
- 다음 단계 기능은 절대 미리 구현하지 않는다

---

### 2. 구조 유지 원칙
- 기존 job 패턴을 그대로 따른다
  - `setup_job_logging`
  - `JobResult`
  - `try_record_job_run`
- 새로운 실행 구조를 만들지 않는다

---

### 3. retention 정책 준수
- 보존 기간은 `data-retention.md`를 따른다
- 임의로 기간을 변경하지 않는다
- 대상 테이블을 확장하지 않는다

---

### 4. 안전장치 원칙

#### dry-run
- 항상 먼저 구현한다
- 실제 삭제를 수행하지 않는다

#### batch delete
- 대량 DELETE를 한 번에 실행하지 않는다
- batch 단위로 나누어 처리한다

---

### 5. 최소 구현 원칙
- 필요한 기능만 구현한다
- 과도한 추상화 금지
- 공용 유틸 과도 생성 금지
- config 시스템 확장 금지

---

### 6. 금지사항

아래 작업은 수행하지 않는다.

- archive 기능 추가
- config/env 구조 변경
- 다른 job 리팩토링
- DB 스키마 변경
- cleanup 범위 확장
- 추가적인 분석/리포트 기능 구현

---

## OUTPUT

응답은 반드시 `output-format.md`를 따른다.

구조:

1. 변경 파일
2. 구현 내용 요약
3. 주의사항
4. 코드

---

## VALIDATION

구현 후 아래 기준을 만족해야 한다.

- current-task.md의 완료 조건 충족
- 기존 job 실행 흐름과 충돌 없음
- 단계 범위를 벗어나지 않음

---

## FAILURE RULE

다음 상황에서는 잘못된 구현으로 간주한다.

- 요구되지 않은 기능이 추가됨
- delete 로직을 dry-run 없이 먼저 구현함
- 기존 구조를 변경함
- cleanup 범위를 확장함
- 코드가 과도하게 복잡해짐

이 경우 구현을 다시 수정해야 한다.