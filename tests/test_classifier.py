"""article_classifier 단위 테스트.

커버 대상:
  app/classifiers/article_classifier.py
"""

import pytest

from app.classifiers.article_classifier import KeywordArticleClassifier

_clf = KeywordArticleClassifier()


class TestKeywordArticleClassifierName:
    def test_classifier_name(self):
        assert _clf.classifier_name == "keyword"


class TestClassifyMarket:
    @pytest.mark.parametrize(
        "title",
        [
            "연준 금리 인하 결정",
            "CPI 예상치 하회",
            "코스피 2% 급락",
            "달러 인덱스 하락",
            "WTI 유가 급등",
            "FOMC 회의 결과",
            "국채 금리 상승",
            "S&P 500 최고치 경신",
            "인플레이션 둔화 확인",
            "GDP 성장률 예상 하회",
            "실업률 개선",
            "경기침체 우려 확산",
        ],
    )
    def test_market_분류(self, title):
        assert _clf.classify(title, "") == "market"


class TestClassifyCompany:
    @pytest.mark.parametrize(
        "title",
        [
            "삼성전자 실적 발표 어닝 서프라이즈",
            "애플 revenue beat 분기 실적",
            "테슬라 CEO 교체 발표",
            "구글 antitrust 소송 제기",
            "아마존 buyback 자사주 매입",
            "마이크로소프트 acquisition 발표",
            "엔비디아 guidance 상향",
        ],
    )
    def test_company_분류(self, title):
        assert _clf.classify(title, "") == "company"


class TestClassifyEvent:
    @pytest.mark.parametrize(
        "title",
        [
            "애플 실적 발표 일정 공개",
            "삼성전자 발표 예정 3분기",
            "공모 일정 확정",
        ],
    )
    def test_event_분류(self, title):
        assert _clf.classify(title, "") == "event"


class TestClassifyGeneral:
    @pytest.mark.parametrize(
        "title",
        [
            "일반적인 뉴스 기사",
            "날씨 관련 소식",
            "스포츠 소식",
        ],
    )
    def test_general_분류(self, title):
        assert _clf.classify(title, "") == "general"


class TestClassifyPriority:
    def test_event_우선순위_highest(self):
        """event + company 키워드 모두 있으면 event 우선."""
        assert _clf.classify("삼성전자 earnings 실적 발표 일정 공개", "") == "event"

    def test_company_우선순위_market보다_높음(self):
        """company + market 키워드 모두 있으면 company 우선."""
        assert _clf.classify("삼성전자 earnings beat 금리 상승 영향", "") == "company"

    def test_summary에서도_분류(self):
        assert _clf.classify("일반 뉴스", "코스피 S&P 500 지수 하락") == "market"
