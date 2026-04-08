# DEPLOYMENT CONTEXT

이 프로젝트는 서버 환경에서 주기적으로 뉴스 수집 및 브리핑 작업을 실행한다.

---

## 운영 목표

1. 정해진 시간에 수집 및 브리핑이 안정적으로 실행될 것
2. 실패 시 로그로 원인을 빠르게 찾을 수 있을 것
3. git pull 및 배포 자동화가 가능할 것
4. 서버 재부팅 후에도 필요한 서비스가 자동으로 복구될 것

---

## 대표 운영 요소

### cron
주기 실행 담당

예:
- collect 작업
- briefing 작업
- all 작업

확인 포인트:
- crontab 시간대
- 실행 사용자
- 로그 리다이렉션
- docker compose 경로
- 권한

---

### docker compose
작업 실행 환경 담당

확인 포인트:
- profile별 역할
- collect / briefing / all 차이
- 컨테이너 종료 후 정리 여부
- 이미지 최신 반영 여부

---

### webhook deploy
푸시 후 자동 배포 담당

확인 포인트:
- git 인증
- 배포 사용자 권한
- pull 실패 원인
- branch 고정 여부
- restart/rebuild 필요 여부

---

### logs
문제 추적의 핵심

최소 확인 대상:
- collect 로그
- briefing 로그
- all 로그
- webhook 로그
- system/journal 로그

---

## 장애 분류 기준

### 1. 코드 문제
예:
- 파싱 실패
- 분류 오류
- DB 저장 오류
- 브리핑 생성 버그

### 2. 환경 문제
예:
- 권한 오류
- docker 실행 실패
- cron PATH 문제
- git 인증 오류
- 환경 변수 누락

### 3. 데이터 문제
예:
- RSS 원문 변경
- 기사 본문 누락
- published_at 이상
- 중복 증가

---

## 운영 대응 원칙

1. 먼저 로그에서 실패 지점 확인
2. collect / process / briefing / deploy 중 어느 단계인지 분리
3. 재현 가능한 최소 명령으로 확인
4. 수정 전 원인 가설을 한 줄로 정리
5. 수정 후 수동 실행으로 검증
6. 자동 실행 복구 여부까지 확인