# -*- coding: utf-8 -*-
"""DuckDB 읽기 전용 조회 helper.

스프링부트(MyBatis)로 이관할 때를 대비해, SQL은 queries.py에 모아두고
이 모듈은 '연결 + 실행 + dict 변환'만 담당한다.
"""
import os
from pathlib import Path
import duckdb

# DB 경로 계산:
#  - 하드코딩된 절대 경로를 쓰지 않고, 이 소스 파일(__file__) 기준의 상대 경로로 찾는다.
#  - pokemon_web/db.py -> 상위(pokemon_web) -> 상위(프로젝트 루트) -> pokemon_champions_data/...
#  - 따라서 프로젝트 폴더를 어디에 두든(작업 폴더 위치와 무관하게) 동일하게 동작한다.
#  - 다른 위치의 DB를 쓰고 싶으면 환경변수 POKEMON_DB로 덮어쓸 수 있다.
_DEFAULT = Path(__file__).resolve().parent.parent / "pokemon_champions_data" / "pokemon_champions.duckdb"
DB_PATH = os.environ.get("POKEMON_DB") or str(_DEFAULT)


def query(sql, params=None):
    """SQL 실행 후 결과를 dict 리스트로 반환."""
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None
