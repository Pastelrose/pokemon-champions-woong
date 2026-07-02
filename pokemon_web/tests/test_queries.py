# -*- coding: utf-8 -*-
"""queries.py 조회 결과 검증 테스트.

기대값은 현재 데이터(레귤레이션 M-A/M-B, 시즌 M-3) 기준이다.
CSV를 갱신해 데이터가 바뀌면 이 기대값도 함께 갱신해야 한다.

스프링부트(MyBatis) 이관 시, 같은 파라미터 조합으로 매퍼 결과를
이 기대값과 비교하면 SQL이 올바르게 옮겨졌는지 확인할 수 있다.
"""
import queries as Q


# ---------- 기본 카운트 ----------

def test_counts():
    counts = {r["테이블"]: r["행수"] for r in Q.counts()}
    assert counts == {
        "pokemon": 323,
        "moves": 749,
        "abilities": 313,
        "items": 148,
        "pokemon_abilities": 664,
        "pokemon_moves": 20416,
        "type_chart": 324,
        "pokemon_usage_rank": 323,
    }


# ---------- 포켓몬 복합 검색 (pokemon_search) ----------
# MyBatis 이관 시 동적 SQL(if/foreach/choose)로 옮길 핵심 부분.
# 파라미터 조합별 기대 건수를 기준값으로 삼는다.

def test_search_no_filter():
    rows = Q.pokemon_search()
    assert len(rows) == 323
    # 기본 정렬: 종족값합계 내림차순
    totals = [r["종족값합계"] for r in rows]
    assert totals == sorted(totals, reverse=True)


def test_search_name():
    rows = Q.pokemon_search(q="리자몽")
    assert sorted(r["이름"] for r in rows) == ["리자몽", "메가리자몽X", "메가리자몽Y"]


def test_search_exclude_mega():
    assert len(Q.pokemon_search(include_mega=False)) == 245


def test_search_types_and():
    rows = Q.pokemon_search(types=["불꽃", "비행"], type_mode="and")
    assert len(rows) == 3
    for r in rows:
        assert {"불꽃", "비행"} <= {r["타입1"], r["타입2"]}


def test_search_types_or():
    assert len(Q.pokemon_search(types=["불꽃", "비행"], type_mode="or")) == 64


def test_search_ability():
    assert len(Q.pokemon_search(ability="위협")) == 19


def test_search_moves_and_or():
    assert len(Q.pokemon_search(moves=["지진", "스톤에지"], move_mode="and")) == 73
    assert len(Q.pokemon_search(moves=["지진", "스톤에지"], move_mode="or")) == 146


def test_search_resists_and():
    # 물/풀 공격을 모두 반감 이하로 받는 포켓몬
    assert len(Q.pokemon_search(resists=["물", "풀"], resist_mode="and")) == 49


def test_search_sort_speed_desc():
    rows = Q.pokemon_search(sort_cols=["스피드"], sort_dirs=["desc"])
    assert rows[0]["이름"] == "메가후딘"
    assert rows[0]["스피드"] == 150


def test_search_sort_whitelist():
    # 화이트리스트에 없는 정렬 컬럼은 무시되고 기본 정렬이 적용된다 (인젝션 방지)
    rows = Q.pokemon_search(sort_cols=["없는컬럼; DROP TABLE pokemon"], sort_dirs=["desc"])
    totals = [r["종족값합계"] for r in rows]
    assert totals == sorted(totals, reverse=True)


# ---------- 포켓몬 상세 ----------

def test_pokemon_detail_and_joins():
    p = Q.pokemon_detail(7)  # 리자몽
    assert p["이름"] == "리자몽"
    assert [a["특성명"] for a in Q.pokemon_abilities(7)] == ["맹화", "선파워"]
    assert len(Q.pokemon_learnset(7)) == 72


def test_pokemon_effectiveness():
    eff = Q.pokemon_effectiveness(7)  # 리자몽 (불꽃/비행)
    weak = sorted(e["공격타입"] for e in eff if e["최종배수"] > 1)
    immune = [e["공격타입"] for e in eff if e["최종배수"] == 0]
    assert weak == ["물", "바위", "전기"]
    assert immune == ["땅"]
    # 바위는 4배 약점
    rock = [e for e in eff if e["공격타입"] == "바위"][0]
    assert rock["최종배수"] == 4


def test_pokemon_detail_not_found():
    assert Q.pokemon_detail(999999) is None


# ---------- 기술 ----------

def test_move_list():
    assert len(Q.move_list()) == 749
    assert len(Q.move_list(type_="불꽃", category="물리")) == 14


def test_move_list_effect_search():
    # 효과 텍스트로도 검색된다
    rows = Q.move_list(q="화상")
    assert len(rows) > 0
    assert any("화상" not in r["기술명"] for r in rows)


def test_move_detail_and_learners():
    m = Q.move_detail(181)  # 지진
    assert m["기술명"] == "지진"
    assert len(Q.move_learners(181)) > 0


# ---------- 특성 / 지닌물건 ----------

def test_ability_list_effect_search():
    assert len(Q.ability_list()) == 313
    rows = Q.ability_list(q="공격")
    assert len(rows) > 0
    assert any("공격" not in r["특성명"] for r in rows)


def test_item_list_and_detail():
    items = Q.item_list()
    assert len(items) == 148
    first = Q.item_detail(items[0]["ID"])
    assert first is not None
    assert "이미지URL" in first and "상세URL" in first


def test_item_detail_not_found():
    assert Q.item_detail(999999) is None


# ---------- 타입 상성표 ----------

def test_type_chart_matrix():
    m = Q.type_chart_matrix()
    assert len(m) == 324  # 18 x 18
    assert m[("전기", "땅")] == 0
    assert m[("물", "불꽃")] == 2
    assert m[("불꽃", "물")] == 0.5
