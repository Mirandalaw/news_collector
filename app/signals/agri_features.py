"""농산물 뉴스 → 일자·품목 피처 테이블 (price-forecast 입력).

흐름:  기사(DB 또는 스냅샷 jsonl) → 품목 태깅 → 사건 클러스터링 → 규칙 평가(AGRI_RULES)
       → magnitude 추출 → (date, item) 집계 → CSV

표준 라이브러리만 쓴다 (폐쇄망 재현 검증에서 pandas 없이도 돌아가야 함).

집계 컬럼 (price-forecast/price_forecast/news.py 와 1:1):
  date, item, news_cnt, posthoc_cnt, event_cnt, dir_sum, dir_wsum, evt_<rule_name>...,
  mag_ton, mag_pct, macro_fx_up, macro_oil_up
  - posthoc_cnt : 제목에 급등·폭등·금배추 같은 사후 보도 표현이 있는 기사 수
                  (이미 가격에 반영된 신호)
  - dir_sum  : 사건별 방향(+1 공급 감소 / −1 공급 증가) 합. 클러스터 1개 = 1표
  - dir_wsum : 방향 × importance 가중(HIGH 1.0 / MEDIUM 0.8 / LOW 0.5)
               × 매체 수 가중(1 + 0.25·(n−1), 최대 1.5) × (숫자 없는 사건 0.5)
  - mag_ton  : 기사 본문에서 뽑은 톤 수량 합 (방출·수매 등), mag_pct : % 수량 (면적·생산량 증감)
  - macro_*  : 그날 경제 기사에서 market_rules 의 DOLLAR_STRONG / OIL_SURGE 발동 건수
               (품목 무관 → 모든 품목 행에 기록, 수입품 중기 보정용)
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from app.db.repositories.briefing_repository import BriefingArticle
from app.signals.models import Direction, Signal
from app.signals.rules import market_rules
from app.signals.rules.agri_rules import AGRI_RULES, IMPORTANCE_WEIGHT, POSTHOC_MARKERS
from app.sources.agri_watchlist import AGRI_WATCHLIST, AgriTagger
from app.utils.hashing import normalize_title

ITEMS = [w.symbol for w in AGRI_WATCHLIST]
MACRO_RULES = {"macro_fx_up": market_rules.DOLLAR_STRONG, "macro_oil_up": market_rules.OIL_SURGE}

# "1만5000톤", "1만 톤", "15,000t", "120ha", "2.7%" — 한국식 '만' 단위를 함께 읽는다
_KNUM = r"(\d[\d,.]*)(?:\s*만\s*(\d[\d,]*)?)?"
_TON = re.compile(_KNUM + r"\s*(?:톤|t\b|ｔ)", re.IGNORECASE)
_PCT = re.compile(r"(\d[\d,.]*)\s*%")
_HA = re.compile(_KNUM + r"\s*(?:ha|헥타르)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 입력
# ---------------------------------------------------------------------------


@dataclass
class RawArticle:
    id: int
    title: str
    summary: str
    source_name: str
    published_at: datetime | None
    url: str = ""
    category: str = ""
    symbols: list[str] = field(default_factory=list)

    @property
    def day(self) -> date | None:
        return self.published_at.date() if self.published_at else None


def read_snapshots(paths: list[Path]) -> list[RawArticle]:
    """scripts/run_agri_collect.py --dump 가 만든 jsonl 들을 읽는다."""
    out: list[RawArticle] = []
    for p in paths:
        with Path(p).open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                pub = r.get("published_at")
                out.append(
                    RawArticle(
                        id=int(r.get("id", 0)),
                        title=r.get("title", ""),
                        summary=r.get("summary") or "",
                        source_name=r.get("source_name", ""),
                        published_at=datetime.fromisoformat(pub) if pub else None,
                        url=r.get("url", ""),
                        category=r.get("category", "농업"),
                        symbols=list(r.get("symbols") or []),
                    )
                )
    return out


# ---------------------------------------------------------------------------
# 태깅 · 클러스터링 · magnitude
# ---------------------------------------------------------------------------


def tag_items(articles: list[RawArticle]) -> list[RawArticle]:
    """AgriTagger 로 다시 태깅한다 (스냅샷에 남은 옛 태거 결과와 무관하게 일관된 기준)."""
    tagger = AgriTagger()
    for a in articles:
        a.symbols = tagger.tag(a.title, a.summary)
    return articles


def _shingles(title: str, n: int = 3) -> set[str]:
    t = re.sub(r"[^\w가-힣]", "", normalize_title(title))
    return {t[i : i + n] for i in range(max(len(t) - n + 1, 1))}


def cluster_events(articles: list[RawArticle], threshold: float = 0.5) -> dict[int, int]:
    """같은 날(±1일)·제목 3-gram 자카드 ≥ threshold 면 같은 사건. 반환: article.id → cluster id.

    클러스터 대표는 먼저 들어온 기사. 규칙 평가는 대표 기사로 하고 매체 수만 가중에 쓴다.
    """
    cid: dict[int, int] = {}
    reps: list[tuple[int, date | None, set[str]]] = []  # (cluster id, day, shingles)
    for a in sorted(articles, key=lambda x: (x.published_at or datetime.min, x.id)):
        sh = _shingles(a.title)
        found = None
        for c, d, s in reps:
            if a.day and d and abs((a.day - d).days) > 1:
                continue
            inter = len(sh & s)
            if inter and inter / len(sh | s) >= threshold:
                found = c
                break
        if found is None:
            found = len(reps)
            reps.append((found, a.day, sh))
        cid[a.id] = found
    return cid


def _num(m: re.Match) -> float:
    """_KNUM 매치 → 숫자. group1 = 앞자리, group2 = '만' 뒤 자리 (없으면 None)."""
    head = float(m.group(1).replace(",", ""))
    if "만" in m.group(0):
        tail = float(m.group(2).replace(",", "")) if m.group(2) else 0.0
        return head * 10000 + tail
    return head


def is_posthoc(title: str) -> bool:
    """제목에 사후 보도 표현(급등·폭등·금배추…)이 있으면 True. 사건 발동과 무관한 별도 플래그."""
    t = title.lower()
    return any(m in t for m in POSTHOC_MARKERS)


def extract_magnitude(text: str) -> dict[str, float]:
    """기사 텍스트의 수량. 톤·ha·% 중 있는 것만.

    가격 숫자(원)는 일부러 안 뽑는다 — 사후 보도가 피처로 새는 경로다.
    """
    out: dict[str, float] = {}
    tons = [_num(m) for m in _TON.finditer(text)]
    if tons:
        out["mag_ton"] = max(tons)
    pct = [float(m.group(1).replace(",", "")) for m in _PCT.finditer(text)]
    if pct:
        out["mag_pct"] = max(pct)
    ha = [_num(m) for m in _HA.finditer(text)]
    if ha:
        out["mag_ha"] = max(ha)
    return out


# ---------------------------------------------------------------------------
# 규칙 평가 → 집계
# ---------------------------------------------------------------------------


def _to_briefing(a: RawArticle) -> BriefingArticle:
    return BriefingArticle(
        id=a.id,
        title=a.title,
        url=a.url,
        source_name=a.source_name,
        summary=a.summary,
        article_type="general",
        published_at=a.published_at,
        collected_at=a.published_at or datetime.now(),
        symbols=list(a.symbols),
    )


def evaluate(articles: list[RawArticle]) -> list[tuple[RawArticle, Signal, int]]:
    """클러스터 대표 기사에 AGRI_RULES 를 적용한다. 반환: (기사, 시그널, 클러스터 매체 수)."""
    cid = cluster_events(articles)
    size: dict[int, int] = defaultdict(int)
    for a in articles:
        size[cid[a.id]] += 1
    seen: set[int] = set()
    out = []
    for a in sorted(articles, key=lambda x: (x.published_at or datetime.min, x.id)):
        c = cid[a.id]
        if c in seen or not a.symbols:
            continue
        seen.add(c)
        ba = _to_briefing(a)
        for rule in AGRI_RULES:
            s = rule.evaluate(ba)
            if s:
                out.append((a, s, size[c]))
    return out


def _dir(d: Direction) -> int:
    return {Direction.BULLISH: 1, Direction.BEARISH: -1}.get(d, 0)


def aggregate_daily(articles: list[RawArticle]) -> list[dict]:
    """(date, item) 행 목록. 기사가 있는 조합만 — 없는 날은 price-forecast 쪽에서 0 처리."""
    articles = tag_items(articles)
    rows: dict[tuple[date, str], dict] = {}
    rule_names = [r.name for r in AGRI_RULES]

    def blank(d: date, item: str) -> dict:
        r = {
            "date": d.isoformat(),
            "item": item,
            "news_cnt": 0,
            "posthoc_cnt": 0,
            "event_cnt": 0,
            "dir_sum": 0,
            "dir_wsum": 0.0,
            "mag_ton": 0.0,
            "mag_pct": 0.0,
            "macro_fx_up": 0,
            "macro_oil_up": 0,
        }
        r.update({f"evt_{n}": 0 for n in rule_names})
        return r

    # 기사 수 (품목별)
    for a in articles:
        if not a.day:
            continue
        for item in a.symbols:
            r = rows.setdefault((a.day, item), blank(a.day, item))
            r["news_cnt"] += 1
            if is_posthoc(a.title):
                r["posthoc_cnt"] += 1

    # 사건 (클러스터 대표 기준)
    for a, s, n_media in evaluate(articles):
        d = _dir(s.direction)
        w = IMPORTANCE_WEIGHT.get(s.importance, 0.5) * min(1 + 0.25 * (n_media - 1), 1.5)
        mag = extract_magnitude(f"{a.title} {a.summary}")
        if not mag:
            w *= 0.5  # 기획서 4-4: 숫자 없는 사건은 감액
        for item in s.symbols or a.symbols:
            r = rows.setdefault((a.day, item), blank(a.day, item))
            r["event_cnt"] += 1
            r["dir_sum"] += d
            r["dir_wsum"] += d * w
            r[f"evt_{s.rule_name}"] += 1
            r["mag_ton"] += mag.get("mag_ton", 0.0)
            r["mag_pct"] += mag.get("mag_pct", 0.0)

    # 거시 (경제 기사, 품목 무관 → 그날 모든 품목 행에 기록)
    macro: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in articles:
        if not a.day or a.category == "농업":
            continue
        ba = _to_briefing(a)
        for key, rule in MACRO_RULES.items():
            if rule.evaluate(ba):
                macro[a.day][key] += 1
    for d, m in macro.items():
        for item in ITEMS:
            r = rows.setdefault((d, item), blank(d, item))
            for key, v in m.items():
                r[key] += v

    return [rows[k] for k in sorted(rows)]


def write_csv(rows: list[dict], path: Path) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


_SELECT = """
SELECT a.id, a.title, COALESCE(a.summary, ''), a.source_name, a.published_at, a.url, a.category,
       COALESCE(array_agg(s.symbol) FILTER (WHERE s.symbol IS NOT NULL), '{}')
FROM news_articles a
LEFT JOIN article_symbols s ON s.article_id = a.id
WHERE a.published_at >= %(since)s
GROUP BY a.id
ORDER BY a.published_at;
"""


def read_db(conn, since: date) -> list[RawArticle]:
    with conn.cursor() as cur:
        cur.execute(_SELECT, {"since": since})
        return [
            RawArticle(
                id=r[0],
                title=r[1],
                summary=r[2],
                source_name=r[3],
                published_at=r[4],
                url=r[5],
                category=r[6],
                symbols=list(r[7]),
            )
            for r in cur.fetchall()
        ]
