# -*- coding: utf-8 -*-
"""사용률 순위만 빠르게 갱신 (매일 cron 실행용).

포켓몬 목록 4~5페이지 + 시즌 페이지만 요청하므로 1분 이내에 끝난다.
pokemon_usage_rank.csv의 현재 시즌 행만 교체하고(과거 시즌 이력 보존),
DB를 재빌드한다.
"""
import sys
import csv
import datetime
import traceback

import config
from config import url, DATA_DIR, NEW_CSV_DIR
from fetch import Fetcher
import parsers
import build_csv
import deploy
import report


def log(msg):
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def main():
    f = Fetcher()
    log("순위 수집 시작")

    rows, page, seen = [], 1, set()
    while page <= 20:
        page_rows = parsers.parse_pokemon_list(f.get(url(f"/pokemon?page={page}")))
        new = [r for r in page_rows if r["ID"] not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["ID"])
        rows += new
        page += 1
    log(f"  포켓몬 {len(rows)}건")

    season, base_date = parsers.parse_season(f.get(url("/usage-ranking")))
    if not season:
        season, base_date = parsers.parse_season(f.get(url("/pokemon/3")))
    if not season:
        log("오류: 시즌 정보를 찾지 못했습니다. 중단.")
        return 1
    log(f"  시즌 {season} (기준일 {base_date})")

    # 안전장치: 기존 포켓몬 수와 크게 다르면 중단
    old_csv = DATA_DIR / "pokemon_db.csv"
    with open(old_csv, encoding="utf-8-sig", newline="") as fp:
        old_ids = {r["ID"] for r in csv.DictReader(fp)}
    matched = sum(1 for r in rows if str(r["ID"]) in old_ids)
    if matched < len(old_ids) * config.MIN_ROW_RATIO:
        log(f"오류: 기존 포켓몬 {len(old_ids)}마리 중 {matched}마리만 수집됨. 중단.")
        return 1

    # 기존 DB에 있는 포켓몬의 순위만 갱신 (신규 포켓몬은 전체 갱신에서 처리)
    rows = [r for r in rows if str(r["ID"]) in old_ids]
    build_csv.build_usage_rank_csv(rows, season, base_date,
                                   DATA_DIR / "pokemon_usage_rank.csv")

    backup_path = deploy.backup_current()
    try:
        import shutil
        shutil.copy2(NEW_CSV_DIR / "pokemon_usage_rank.csv",
                     DATA_DIR / "pokemon_usage_rank.csv")
        counts = deploy.rebuild_db()
        log(f"재빌드 완료: {counts}")
    except Exception:
        log("실패. 백업으로 되돌립니다.")
        traceback.print_exc()
        deploy.restore_backup(backup_path)
        return 1
    deploy.prune_backups(keep=10)
    log("순위 갱신 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
