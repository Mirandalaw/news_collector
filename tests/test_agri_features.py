"""agri_features: 클러스터링·magnitude·집계 (DB 불필요)."""

import json
from datetime import datetime

from app.signals import agri_features as AF


def _a(i, title, day="2026-10-20", summary="", src="t", cat="농업", symbols=None):
    return AF.RawArticle(
        id=i,
        title=title,
        summary=summary,
        source_name=src,
        published_at=datetime.fromisoformat(f"{day}T09:00:00+09:00"),
        category=cat,
        symbols=symbols or [],
    )


def test_cluster_same_event_across_media():
    arts = [
        _a(1, "정부, 가을배추 비축물량 1만톤 방출 결정"),
        _a(2, "정부 가을배추 비축물량 1만톤 방출 결정…김장철 대비", src="u"),
        _a(3, "해남 배추 산지 폭우 피해 확산"),
    ]
    cid = AF.cluster_events(arts)
    assert cid[1] == cid[2] != cid[3]


def test_magnitude_extraction():
    m = AF.extract_magnitude("비축 배추 1만5000톤 방출, 재배면적 2.7% 감소, 피해 면적 120ha")
    assert m["mag_ton"] == 15000 and m["mag_pct"] == 2.7 and m["mag_ha"] == 120
    assert AF.extract_magnitude("배추 한 포기 9,000원") == {}


def test_aggregate_counts_one_event_per_cluster_and_weights():
    arts = [
        _a(1, "정부, 가을배추 비축물량 1만톤 방출 결정"),
        _a(2, "정부 가을배추 비축물량 1만톤 방출 결정…김장철 대비", src="u"),
        _a(3, "해남 배추 산지 폭우 피해 확산"),
        _a(4, "김치찌개 맛집 배추 레시피"),
    ]
    rows = AF.aggregate_daily(arts)
    r = {(x["date"], x["item"]): x for x in rows}[("2026-10-20", "배추")]
    assert r["news_cnt"] == 3  # 레시피 기사는 품목 태깅에서 제외
    assert r["event_cnt"] == 2  # 방출(클러스터 1) + 폭우
    assert r["evt_agri_reserve_release"] == 1 and r["evt_agri_heavy_rain"] == 1
    assert r["dir_sum"] == 0  # −1 + 1
    assert r["mag_ton"] == 10000
    # 방출: HIGH 1.0 × 매체2 1.25 = −1.25 / 폭우: HIGH 1.0 × 숫자없음 0.5 = +0.5
    assert abs(r["dir_wsum"] - (-1.25 + 0.5)) < 1e-9


def test_macro_rows_apply_to_all_items():
    arts = [_a(9, "원·달러 환율 1,450원 돌파…달러 강세 지속", cat="경제")]
    rows = AF.aggregate_daily(arts)
    assert {x["item"] for x in rows} == set(AF.ITEMS)
    assert all(x["macro_fx_up"] >= 1 for x in rows)


def test_snapshot_roundtrip(tmp_path):
    p = tmp_path / "2026-10-20.jsonl"
    rec = {
        "id": 1,
        "source_name": "t",
        "title": "무 산지 출하 지연, 반입량 감소",
        "url": "u",
        "published_at": "2026-10-20T09:00:00+09:00",
        "summary": "",
        "collected_at": None,
        "symbols": ["무"],
    }
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    arts = AF.read_snapshots([p])
    rows = AF.aggregate_daily(arts)
    assert rows[0]["item"] == "무" and rows[0]["evt_agri_shipment_delay"] == 1
