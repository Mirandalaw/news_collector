# SKILL: dedup-design

## ROLE
뉴스 중복 제거와 이벤트 그룹핑 기준을 설계한다.

---

## INPUT
- article 테이블 구조
- 현재 dedup 로직
- title / source / url / published_at 데이터 예시
- 브리핑 생성 로직
- 실제 중복 사례

---

## TASK

1. 현재 dedup이 어디서 동작하는지 확인한다
- collector
- repository
- briefing builder
- DB unique constraint

2. 중복을 레벨별로 나눈다
- 완전 중복
- 준중복
- 동일 이벤트

3. event grouping 설계를 제안한다
- 대표 제목 생성
- cluster key 후보
- 대표 기사 선정 기준

4. 성능 관점도 함께 본다
- 실시간 비교 범위
- 최근 N일 대상 제한
- 인덱스 필요 여부

---

## OUTPUT FORMAT

[중복 제거 설계]
- 현재 방식:
- 문제점:
- 개선 목표:

[중복 레벨 정의]
- 레벨 1:
- 레벨 2:
- 레벨 3:

[이벤트 그룹핑 설계]
- 기준 필드:
- 대표 이벤트 생성 방식:
- 대표 기사 선정 기준:

[구현 포인트]
- DB:
- 애플리케이션 로직:
- 브리핑 반영 방식:

[리스크]
- 오탐 위험:
- 미탐 위험:
- 성능 리스크: