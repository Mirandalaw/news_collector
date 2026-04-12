# SIGNAL AGGREGATION

## 목적
생성된 signal들을 시장 단위와 종목 단위로 집계하여
실제 매매 판단에 사용할 수 있는 점수 구조를 만든다.

---

## 현재 상태

- 기사별 signal 생성 가능
- signal dedup 완료
- signal scoring MVP 구현 완료

하지만 아직 score_signals는 단순히 signal 리스트를 점수화하는 순수 함수에 머물러 있다.

다음 단계는 signal들을 실제 사용 단위로 묶어
시장 점수와 종목 점수를 계산하는 것이다.

---

## 목표

1. 시장 관련 signal 집계
2. 종목별 signal 집계
3. score_signals 재사용
4. 결과를 추후 매매 판단에 연결 가능한 구조로 만든다

---

## 집계 단위

### 1. market
시장 관련 기사에서 생성된 signal들을 모아 하나의 시장 점수 계산

### 2. symbol
동일 종목(symbol)에 속한 signal들을 모아 종목별 점수 계산

---

## 설계 원칙

1. score_signals를 재사용한다
2. 집계 로직과 점수 계산 로직을 분리한다
3. 초기 버전은 단순 dictionary 기반으로 구현한다
4. 자동매매 실행 로직은 아직 포함하지 않는다

---

## 출력 형태 예시

- market_score: ScoreResult
- by_symbol: dict[str, ScoreResult]

---

## 금지사항

- 주문 실행
- 차트/가격 필터 결합
- 동적 threshold 조정
- ML 모델 도입