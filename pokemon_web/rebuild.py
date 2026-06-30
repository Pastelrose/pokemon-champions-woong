# -*- coding: utf-8 -*-
"""rebuild_db.sql을 실행해 메인 DuckDB를 재빌드하는 모듈(관리자용).

 - rebuild_db.sql 내부의 상대 CSV 경로(read_csv_auto('xxx.csv'))를 데이터 폴더 기준
   절대 경로로 바꿔 실행하므로, 서버의 실행 위치(CWD)와 무관하게 동작한다.
 - 동시에 두 번 재빌드되지 않도록 Lock으로 직렬화한다.
 - 재빌드는 쓰기 연결을 잡으므로, 마침 진행 중인 조회(read_only)와 잠깐 충돌할 수 있어
   쓰기 연결 획득을 several번 재시도한다.
"""
import re
import time
import threading
from pathlib import Path

import duckdb

from db import DB_PATH

_DATA_DIR = Path(DB_PATH).resolve().parent
_SQL_PATH = _DATA_DIR / "rebuild_db.sql"
_lock = threading.Lock()


def _connect_rw(retries=10, delay=0.3):
    """쓰기 연결 획득(조회 연결과의 일시적 잠금 충돌에 대비해 재시도)."""
    last = None
    for _ in range(retries):
        try:
            return duckdb.connect(str(DB_PATH))
        except Exception as e:  # 잠금 충돌 등
            last = e
            time.sleep(delay)
    raise last


def _split_statements(sql: str):
    for part in sql.split(";"):
        s = part.strip()
        if s:
            yield s


def rebuild_database():
    """rebuild_db.sql을 실행하고, 마지막 카운트 SELECT 결과를 dict로 반환."""
    with _lock:
        sql = _SQL_PATH.read_text(encoding="utf-8")
        # 상대 CSV 경로 -> 데이터 폴더 절대 경로
        base = _DATA_DIR.as_posix()
        sql = re.sub(r"read_csv_auto\('", f"read_csv_auto('{base}/", sql)

        con = _connect_rw()
        counts = {}
        try:
            for stmt in _split_statements(sql):
                cur = con.execute(stmt)
                # 앞쪽 주석(-- ...)을 제거한 실제 시작 키워드로 SELECT 여부 판단
                effective = "\n".join(
                    ln for ln in stmt.splitlines() if not ln.strip().startswith("--")
                ).strip().upper()
                if effective.startswith("SELECT"):
                    for row in cur.fetchall():
                        counts[row[0]] = row[1]  # (테이블명, 행수)
        finally:
            con.close()
        return counts
