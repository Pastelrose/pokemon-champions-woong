# -*- coding: utf-8 -*-
"""백업 -> CSV 교체 -> DuckDB 재빌드."""
import re
import shutil
import datetime
from pathlib import Path

import duckdb

from config import DATA_DIR, DB_PATH, SQL_PATH, BACKUP_DIR, CSV_FILES


def backup_current():
    """현재 CSV + DB를 backup/타임스탬프/ 폴더로 복사. 백업 경로 반환."""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for name in CSV_FILES:
        src = DATA_DIR / name
        if src.exists():
            shutil.copy2(src, dest / name)
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, dest / DB_PATH.name)
    return dest


def prune_backups(keep=10):
    """오래된 백업 폴더는 최근 keep개만 남기고 삭제."""
    if not BACKUP_DIR.exists():
        return
    dirs = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir()])
    for d in dirs[:-keep]:
        shutil.rmtree(d, ignore_errors=True)


def deploy_csvs(new_dir):
    """검증을 통과한 새 CSV를 데이터 폴더로 복사."""
    new_dir = Path(new_dir)
    for name in CSV_FILES:
        src = new_dir / name
        if src.exists():
            shutil.copy2(src, DATA_DIR / name)


def rebuild_db():
    """rebuild_db.sql을 실행해 DuckDB 재생성. 테이블별 행수 dict 반환.

    (pokemon_web/rebuild.py와 같은 방식: 상대 CSV 경로를 절대 경로로 치환)
    """
    sql = SQL_PATH.read_text(encoding="utf-8")
    base = DATA_DIR.as_posix()
    sql = re.sub(r"read_csv_auto\('", f"read_csv_auto('{base}/", sql)
    con = duckdb.connect(str(DB_PATH))
    counts = {}
    try:
        for part in sql.split(";"):
            stmt = part.strip()
            if not stmt:
                continue
            cur = con.execute(stmt)
            effective = "\n".join(
                ln for ln in stmt.splitlines() if not ln.strip().startswith("--")
            ).strip().upper()
            if effective.startswith("SELECT"):
                for row in cur.fetchall():
                    counts[row[0]] = row[1]
    finally:
        con.close()
    return counts


def restore_backup(backup_dir):
    """문제 발생 시 백업 폴더의 CSV/DB로 되돌린다."""
    backup_dir = Path(backup_dir)
    for name in CSV_FILES:
        src = backup_dir / name
        if src.exists():
            shutil.copy2(src, DATA_DIR / name)
    db = backup_dir / DB_PATH.name
    if db.exists():
        shutil.copy2(db, DB_PATH)
