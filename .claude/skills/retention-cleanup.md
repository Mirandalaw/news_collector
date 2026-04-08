# SKILL: retention-cleanup

## ROLE
데이터 보존 정책과 cleanup job 설계를 정리한다.

---

## INPUT
- article / summary / briefing / log 관련 테이블 구조
- 현재 데이터 적재량
- 브리핑 생성 재처리 필요성
- 운영 로그 저장 방식
- cron / job 구조

---

## TASK

1. 테이블별 성격 분류
- 원문성
- 파생 데이터
- 최종 산출물
- 운영 로그

2. 보존 전략 제안
- keep
- archive
- delete

3. cleanup 실행 방식 제안
- cron
- app job
- SQL batch
- 파티셔닝 필요 여부

4. 운영 안전장치 제안
- dry-run
- 삭제 건수 로그
- 백업
- 순차 삭제

---

## OUTPUT FORMAT

[보존 정책 설계]
- 테이블:
- 데이터 성격:
- 권장 보존 기간:
- 권장 처리 방식:

[cleanup 설계]
- 실행 주기:
- 실행 방식:
- 안전장치:
- 로그 방식:

[운영 리스크]
- 과삭제 위험:
- 성능 영향:
- 복구 고려사항: