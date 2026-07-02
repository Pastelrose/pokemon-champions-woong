# -*- coding: utf-8 -*-
"""모든 SQL을 한 곳에 모아둔다. (스프링부트 MyBatis 매퍼로 1:1 이관 용이)"""
from db import query, query_one

TYPES = ["노말","불꽃","물","풀","전기","얼음","격투","독","땅","비행",
         "에스퍼","벌레","바위","고스트","드래곤","악","강철","페어리"]

# 정렬 가능한 컬럼 화이트리스트 (SQL 인젝션 방지)
SORT_COLUMNS = {
    "종족값합계": "종족값합계", "HP": "HP", "공격": "공격", "방어": "방어",
    "특공": "특공", "특방": "특방", "스피드": "스피드",
    "싱글순위": "싱글순위", "더블순위": "더블순위", "이름": "이름",
}

# 기술 정렬 화이트리스트 (값 -> ORDER BY 식). 위력/명중/PP는 INTEGER 컬럼.
MOVE_SORT_COLUMNS = {
    "타입": "타입",
    "분류": "분류",
    "위력": "위력",
    "명중": "명중",
    "PP": "PP",
    "기술명": "기술명",
}

# 사용 순위는 별도 테이블(pokemon_usage_rank)에서 최신 기준일 기준으로 조인
LATEST_RANK_JOIN = """LEFT JOIN (
    SELECT pokemon_id, 싱글순위, 더블순위 FROM pokemon_usage_rank
    WHERE 기준일 = (SELECT max(기준일) FROM pokemon_usage_rank)
) ur ON ur.pokemon_id = p.ID"""


def counts():
    return query("""
        SELECT 'pokemon' AS 테이블, count(*) AS 행수 FROM pokemon
        UNION ALL SELECT 'moves', count(*) FROM moves
        UNION ALL SELECT 'abilities', count(*) FROM abilities
        UNION ALL SELECT 'items', count(*) FROM items
        UNION ALL SELECT 'pokemon_abilities', count(*) FROM pokemon_abilities
        UNION ALL SELECT 'pokemon_moves', count(*) FROM pokemon_moves
        UNION ALL SELECT 'type_chart', count(*) FROM type_chart
        UNION ALL SELECT 'pokemon_usage_rank', count(*) FROM pokemon_usage_rank
    """)


def ability_names():
    return [r["특성명"] for r in query("SELECT 특성명 FROM abilities ORDER BY 특성명")]


def move_names():
    return [r["기술명"] for r in query("SELECT 기술명 FROM moves ORDER BY 기술명")]


def _combine(subs, mode):
    """subs: [(sql, [params]), ...] 를 AND 또는 OR로 결합."""
    subs = [x for x in subs if x]
    if not subs:
        return None, []
    joiner = " OR " if str(mode).lower() == "or" else " AND "
    sql = "(" + joiner.join(s for s, _ in subs) + ")"
    params = [p for _, ps in subs for p in ps]
    return sql, params


def pokemon_search(q="", types=None, type_mode="and", ability="",
                   moves=None, move_mode="and", resists=None, resist_mode="and",
                   include_mega=True, sort_cols=None, sort_dirs=None):
    """복합 조건 포켓몬 검색.

    다중 선택 항목(타입/기술/내성타입)은 type_mode/move_mode/resist_mode 로
    AND(모두 만족) 또는 OR(하나 이상) 결합을 선택한다.
    """
    types = [t for t in (types or []) if t][:2]
    moves = [m for m in (moves or []) if m][:4]
    resists = [r for r in (resists or []) if r]

    where, params = [], []
    if q:
        where.append("p.이름 ILIKE '%' || ? || '%'")
        params.append(q)

    # 타입 (AND/OR)
    tsubs = [("(p.타입1 = ? OR p.타입2 = ?)", [t, t]) for t in types]
    csql, cpar = _combine(tsubs, type_mode)
    if csql:
        where.append(csql); params += cpar

    if ability:
        where.append("EXISTS (SELECT 1 FROM pokemon_abilities pa "
                     "JOIN abilities a ON pa.ability_id = a.ID "
                     "WHERE pa.pokemon_id = p.ID AND a.특성명 = ?)")
        params.append(ability)

    # 기술 (AND/OR)
    msubs = [("EXISTS (SELECT 1 FROM pokemon_moves pm JOIN moves m ON pm.move_id = m.ID "
              "WHERE pm.pokemon_id = p.ID AND m.기술명 = ?)", [mv]) for mv in moves]
    csql, cpar = _combine(msubs, move_mode)
    if csql:
        where.append(csql); params += cpar

    # 내성 타입 (AND/OR)
    rsubs = [("EXISTS (SELECT 1 FROM pokemon_type_effectiveness e "
              "WHERE e.pokemon_id = p.ID AND e.공격타입 = ? AND e.최종배수 < 1)", [r]) for r in resists]
    csql, cpar = _combine(rsubs, resist_mode)
    if csql:
        where.append(csql); params += cpar

    if not include_mega:
        where.append("p.이름 NOT LIKE '%메가%'")

    sql = ("SELECT p.ID, p.이름, p.타입1, p.타입2, p.HP, p.공격, p.방어, p.특공, p.특방, "
           "p.스피드, p.종족값합계, ur.싱글순위, ur.더블순위 FROM pokemon p " + LATEST_RANK_JOIN)
    if where:
        sql += " WHERE " + " AND ".join(where)

    order = []
    for col, d in zip(sort_cols or [], sort_dirs or []):
        if col in SORT_COLUMNS:
            direction = "DESC" if str(d).lower() in ("desc", "역순") else "ASC"
            clause = SORT_COLUMNS[col] + " " + direction
            if col in ("싱글순위", "더블순위"):
                clause += " NULLS LAST"
            order.append(clause)
    if not order:
        order = ["종족값합계 DESC"]
    sql += " ORDER BY " + ", ".join(order)
    return query(sql, params)


def pokemon_detail(pid):
    return query_one(
        "SELECT p.*, ur.싱글순위, ur.더블순위 FROM pokemon p " + LATEST_RANK_JOIN +
        " WHERE p.ID = ?", [pid])


def pokemon_abilities(pid):
    return query("""
        SELECT a.ID, a.특성명, a.효과, pa.slot
        FROM pokemon_abilities pa JOIN abilities a ON pa.ability_id = a.ID
        WHERE pa.pokemon_id = ? ORDER BY pa.slot
    """, [pid])


def pokemon_learnset(pid):
    return query("""
        SELECT mv.ID, mv.기술명, mv.타입, mv.분류, mv.위력, mv.명중, mv.PP, mv.대상, mv.효과
        FROM pokemon_moves pm JOIN moves mv ON pm.move_id = mv.ID
        WHERE pm.pokemon_id = ?
        ORDER BY mv.타입, mv.위력 DESC NULLS LAST, mv.기술명
    """, [pid])


def pokemon_effectiveness(pid):
    return query("""
        SELECT 공격타입, 최종배수 FROM pokemon_type_effectiveness
        WHERE pokemon_id = ? AND 최종배수 <> 1
        ORDER BY 최종배수 DESC, 공격타입
    """, [pid])


def move_list(q="", type_="", category="", sort_cols=None, sort_dirs=None):
    where, params = [], []
    if q:
        # 기술명 또는 효과 텍스트에 포함되면 검색됨
        where.append("(기술명 ILIKE '%' || ? || '%' OR 효과 ILIKE '%' || ? || '%')")
        params += [q, q]
    if type_:
        where.append("타입 = ?"); params.append(type_)
    if category:
        where.append("분류 = ?"); params.append(category)
    sql = "SELECT ID, 기술명, 타입, 분류, 위력, 명중, PP, 대상 FROM moves"
    if where:
        sql += " WHERE " + " AND ".join(where)
    order = []
    for col, d in zip(sort_cols or [], sort_dirs or []):
        if col in MOVE_SORT_COLUMNS:
            direction = "DESC" if str(d).lower() in ("desc", "역순") else "ASC"
            order.append(MOVE_SORT_COLUMNS[col] + " " + direction + " NULLS LAST")
    if not order:
        order = ["기술명 ASC"]
    sql += " ORDER BY " + ", ".join(order)
    return query(sql, params)


def move_detail(mid):
    return query_one("SELECT * FROM moves WHERE ID = ?", [mid])


def move_learners(mid):
    return query("""
        SELECT p.ID, p.이름, p.타입1, p.타입2, p.종족값합계
        FROM pokemon_moves pm JOIN pokemon p ON pm.pokemon_id = p.ID
        WHERE pm.move_id = ? ORDER BY p.이름
    """, [mid])


def ability_list(q=""):
    if q:
        # 특성명 또는 효과 텍스트에 포함되면 검색됨
        return query("SELECT ID, 특성명, 효과 FROM abilities "
                     "WHERE 특성명 ILIKE '%' || ? || '%' OR 효과 ILIKE '%' || ? || '%' "
                     "ORDER BY 특성명", [q, q])
    return query("SELECT ID, 특성명, 효과 FROM abilities ORDER BY 특성명")


def ability_detail(aid):
    return query_one("SELECT * FROM abilities WHERE ID = ?", [aid])


def ability_pokemon(aid):
    return query("""
        SELECT p.ID, p.이름, p.타입1, p.타입2
        FROM pokemon_abilities pa JOIN pokemon p ON pa.pokemon_id = p.ID
        WHERE pa.ability_id = ? ORDER BY p.이름
    """, [aid])


def item_list(q=""):
    if q:
        # 이름 또는 효과 텍스트에 포함되면 검색됨
        return query("SELECT ID, 이름, 효과, 입수방법 FROM items "
                     "WHERE 이름 ILIKE '%' || ? || '%' OR 효과 ILIKE '%' || ? || '%' "
                     "ORDER BY 이름", [q, q])
    return query("SELECT ID, 이름, 효과, 입수방법 FROM items ORDER BY 이름")


def item_detail(iid):
    return query_one("SELECT * FROM items WHERE ID = ?", [iid])


def type_chart_matrix():
    rows = query("SELECT 공격타입, 방어타입, 배수 FROM type_chart")
    m = {}
    for r in rows:
        m[(r["공격타입"], r["방어타입"])] = r["배수"]
    return m
