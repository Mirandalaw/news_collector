"""농산물 가격예측용 RSS 소스 (해커톤 트랙 A·B).

2026-10-13 기준 실제 응답 확인된 피드만 넣는다. 세 매체 모두 ndsoft CMS라
`/rss/allArticle.xml` 패턴이며 최신 50건을 돌려준다.

category="농업" 으로 통일해 기존 경제 피드와 구분한다. cleanup_job의 보존기간 예외와
agri_watchlist 태깅은 이 category 값을 기준으로 동작한다.

미확인 소스 (브라우저에서 RSS 제공 여부 확인 후 추가):
  - 농민신문 nongmin.com            : robots 차단으로 자동 확인 불가
  - 농식품부 보도자료 mafra.go.kr    : RSS 미확인. 대안: 정책브리핑(korea.kr) 부처별 RSS,
                                      또는 공공데이터포털 '농림축산식품부 보도자료' API
  - 기상 특보                         : RSS 대신 공공데이터포털 기상특보 조회서비스 API 사용
"""

from app.collectors.rss_collector import RssSource

AGRI_CATEGORY = "농업"

AGRI_SOURCES: list[RssSource] = [
    RssSource(
        url="https://www.agrinet.co.kr/rss/allArticle.xml",
        source_name="한국농어민신문",
        category=AGRI_CATEGORY,
    ),
    RssSource(
        url="https://www.aflnews.co.kr/rss/allArticle.xml",
        source_name="농수축산신문",
        category=AGRI_CATEGORY,
    ),
    RssSource(
        url="https://www.amnews.co.kr/rss/allArticle.xml",
        source_name="농축유통신문",
        category=AGRI_CATEGORY,
    ),
]
