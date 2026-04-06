# News Collector MVP (PostgreSQL 기반)

## 1. 프로젝트 개요

이 프로젝트는 투자 판단 보조용 뉴스 자동화 시스템의 1단계다.

현재 단계의 목적은:
- 뉴스 데이터를 안정적으로 수집
- 중복 제거
- DB 저장
- 이후 AI 분석 및 브리핑 생성의 기반 구축

이번 단계에서는 **뉴스 수집 파이프라인 구축에만 집중한다.**

---

## 2. 목표

1. RSS 기반 뉴스 수집
2. 데이터 정제
3. 중복 제거
4. PostgreSQL 저장
5. 확장 가능한 구조 설계

---

## 3. 구현 범위 (중요)

### 포함
- RSS 뉴스 수집
- PostgreSQL 저장
- URL 기준 중복 제거
- logging 적용
- 예외 처리
- 모듈 구조 설계

### 제외
- AI 요약
- 감성 분석
- 텔레그램
- Notion
- 크롤링
- Selenium
- 스케줄러
- Docker

---

## 4. 기술 스택

- Python 3.10+
- PostgreSQL
- psycopg2
- feedparser
- logging

---

## 5. DB 설계

### news_articles

```sql
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at TIMESTAMPTZ,
    summary TEXT,
    collected_at TIMESTAMPTZ NOT NULL
);

인덱스
CREATE INDEX IF NOT EXISTS idx_news_published_at
ON news_articles (published_at DESC);

6. 데이터 처리 규칙
필수 필드
title
url
source_name
category
collected_at
선택 필드
published_at
summary
7. 데이터 정제
공백 제거
title/url 없으면 skip
summary 없으면 빈 문자열
시간은 UTC 기준
8. 중복 처리
URL 기준 UNIQUE
중복 시 insert skip
9. RSS 수집 규칙
소스별 실패 허용 (continue)
전체 수집 중단 금지
소스별 로그 기록
10. DB 규칙
psycopg2 사용
ORM 사용 금지
SQL 직접 작성
transaction 명확히 처리
insert 실패 시 continue
11. 로깅

print 금지

필수 로그:

수집 시작/종료
소스별 처리
저장 성공/실패
중복 스킵
12. 프로젝트 구조
news_collector/
├─ app/
│  ├─ config/
│  │  └─ settings.py
│  ├─ db/
│  │  ├─ connection.py
│  │  ├─ schema.py
│  │  └─ news_repository.py
│  ├─ collectors/
│  │  └─ rss_collector.py
│  ├─ services/
│  │  └─ news_ingestion_service.py
│  ├─ utils/
│  │  ├─ datetime_utils.py
│  │  └─ logger.py
│  └─ sources/
│     └─ rss_sources.py
├─ scripts/
│  └─ run_news_collection.py
├─ tests/
├─ docs/
├─ pyproject.toml
└─ README.md
13. 구현 원칙
함수 단위 분리
타입 힌트 필수
단일 책임 원칙
예외 처리 필수
하드코딩 금지
14. 실행 흐름
DB 연결
테이블 생성
RSS 수집
데이터 정제
DB 저장
로그 출력
15. Claude 역할

Claude는 단순 코드 생성기가 아니라
백엔드 시스템 엔지니어 역할로 구현한다

16. 금지사항
한 파일 몰아넣기
print 사용
예외 처리 없는 코드
임시 코드
ORM 사용
이모지는 사용 여부 : X
17. 완료 기준
python main.py 실행 가능
DB 저장 정상 동작
중복 제거 동작
로그 출력 확인
18. 코드 및 API 문서화 원칙

새로운 코드, 함수, 클래스, API를 작성하거나 수정할 때마다 간단한 주석 또는 별도의 문서(Markdown 등)로 설명을 남긴다.
주요 함수/클래스에는 입력값, 반환값, 예외, 사용 예시 등을 명확히 작성한다.
외부 API 연동 시, 엔드포인트/파라미터/응답 예시/주의사항 등을 정리한다.
문서는 /docs 폴더 또는 각 모듈/파일 상단에 관리한다.