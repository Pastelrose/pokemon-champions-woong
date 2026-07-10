# -*- coding: utf-8 -*-
"""전체 데이터 갱신 파이프라인 (cron 주기 실행용).

흐름: 수집 -> 변환(CSV) -> 검증 -> 백업 -> 적재 -> DB 재빌드 -> 리포트
검증 실패 시 적재하지 않고 기존 데이터를 유지한 채 종료 코드 1로 끝난다.

사용법:
  python3 update_all.py               # 전체 갱신
  python3 update_all.py --dry-run     # 적재 없이 수집/검증/리포트만
  python3 update_all.py --limit 5     # 상세 페이지 5건만(파서 점검용)
  python3 update_all.py --probe       # 페이지별 원본 HTML만 work/html/에 저장
"""
import sys
import argparse
import datetime
import traceback

import config
from config import url, DATA_DIR, NEW_CSV_DIR, HTML_DIR, WORK_DIR
from fetch import Fetcher
import parsers
import build_csv
import validate
import deploy
import report


def log(msg):
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def fetch_all_pokemon_pages(f, locale, max_pages=20):
    """페이지네이션을 따라가며 포켓몬 목록 행을 모두 수집."""
    rows, page = [], 1
    seen = set()
    while page <= max_pages:
        html = f.get(url(f"/pokemon?page={page}", locale))
        if locale == config.LOCALE:
            page_rows = parsers.parse_pokemon_list(html)
            new = [r for r in page_rows if r["ID"] not in seen]
        else:
            names = parsers.parse_pokemon_names(html)
            new = [{"ID": k, "이름": v} for k, v in names.items() if k not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["ID"])
        rows += new
        page += 1
    return rows


def probe(f):
    """대표 페이지의 원본 HTML을 저장해 파서 점검에 사용."""
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    targets = {
        "pokemon_list_p1.html": url("/pokemon?page=1"),
        "moves_list.html": url("/moves"),
        "abilities_list.html": url("/abilities"),
        "items_list.html": url("/items"),
        "usage_ranking.html": url("/usage-ranking"),
        "pokemon_detail_3.html": url("/pokemon/3"),
    }
    for name, u in targets.items():
        (HTML_DIR / name).write_text(f.get(u), encoding="utf-8")
        log(f"저장: work/html/{name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="적재 없이 검증/리포트까지만")
    ap.add_argument("--limit", type=int, default=0, help="상세 페이지 수집 개수 제한(테스트용)")
    ap.add_argument("--probe", action="store_true", help="원본 HTML만 저장하고 종료")
    args = ap.parse_args()

    f = Fetcher()
    if args.probe:
        probe(f)
        return 0

    log("1/6 수집 시작")
    pokemon_rows = fetch_all_pokemon_pages(f, config.LOCALE)
    log(f"  포켓몬 목록 {len(pokemon_rows)}건")
    en_rows = fetch_all_pokemon_pages(f, config.LOCALE_EN)
    en_names = {r["ID"]: r["이름"] for r in en_rows}
    log(f"  영어 이름 {len(en_names)}건")
    move_rows = parsers.parse_moves_list(f.get(url("/moves")))
    log(f"  기술 {len(move_rows)}건")
    ability_rows = parsers.parse_abilities_list(f.get(url("/abilities")))
    log(f"  특성 {len(ability_rows)}건")
    item_rows = parsers.parse_items_list(f.get(url("/items")))
    log(f"  지닌물건 {len(item_rows)}건")
    season, base_date = parsers.parse_season(f.get(url("/usage-ranking")))
    if not season:
        season, base_date = parsers.parse_season(f.get(url("/pokemon/3")))
    log(f"  시즌 {season} (기준일 {base_date})")

    targets = sorted(pokemon_rows, key=lambda x: x["ID"])
    if args.limit:
        targets = targets[:args.limit]
    log(f"2/6 상세 페이지(배우는 기술) {len(targets)}건 수집 "
        f"(약 {len(targets) * config.REQUEST_DELAY_SEC / 60:.0f}분 예상)")
    learnsets, failed = {}, []
    for i, p in enumerate(targets, 1):
        try:
            ls = parsers.parse_learnset(f.get(url(f"/pokemon/{p['ID']}")))
            learnsets[p["ID"]] = ls
            if not ls:
                failed.append((p["ID"], p["이름"], "learnset 0건"))
        except Exception as e:
            failed.append((p["ID"], p["이름"], str(e)))
        if i % 50 == 0:
            log(f"  ... {i}/{len(targets)}")
    if failed:
        log(f"  경고: 상세 수집 실패/0건 {len(failed)}건 -> {failed[:5]}")

    log("3/6 CSV 생성")
    build_csv.build_pokemon_csv(pokemon_rows, en_names)
    build_csv.build_moves_csv(move_rows)
    build_csv.build_abilities_csv(ability_rows)
    build_csv.build_items_csv(item_rows)
    _, missing = build_csv.build_pokemon_abilities_csv(pokemon_rows, ability_rows)
    if missing:
        log(f"  경고: 특성 이름 매핑 실패 {len(missing)}건 -> {missing[:5]}")
    build_csv.build_pokemon_moves_csv(learnsets, pokemon_rows)
    if not season:
        log("오류: 시즌 정보를 찾지 못해 순위 갱신 불가")
        return 1
    build_csv.build_usage_rank_csv(pokemon_rows, season, base_date,
                                   DATA_DIR / "pokemon_usage_rank.csv")

    log("4/6 검증")
    errors = validate.validate_all(NEW_CSV_DIR, DATA_DIR)
    if errors:
        log(f"검증 실패 {len(errors)}건. 갱신을 중단합니다 (기존 데이터 유지).")
        for e in errors[:20]:
            log("  - " + e)
        path, _ = report.make_report(DATA_DIR, NEW_CSV_DIR,
                                     ["결과: 검증 실패로 미적용"] + errors[:50])
        log(f"리포트: {path}")
        return 1

    extra = [f"요청 수: {f.count}", f"시즌: {season} ({base_date})"]
    if args.dry_run:
        path, summary = report.make_report(DATA_DIR, NEW_CSV_DIR,
                                           ["결과: dry-run (적용 안 함)"] + extra)
        log(f"dry-run 완료. 리포트: {path}")
        log(summary)
        return 0

    log("5/6 백업 후 적재")
    backup_path = deploy.backup_current()
    log(f"  백업: {backup_path}")
    try:
        deploy.deploy_csvs(NEW_CSV_DIR)
        counts = deploy.rebuild_db()
        log(f"  재빌드 완료: {counts}")
    except Exception:
        log("적재/재빌드 실패. 백업으로 되돌립니다.")
        traceback.print_exc()
        deploy.restore_backup(backup_path)
        return 1
    deploy.prune_backups(keep=10)

    log("6/6 리포트")
    path, summary = report.make_report(backup_path, DATA_DIR,
                                       ["결과: 적용 완료"] + extra)
    log(f"리포트: {path}")
    log(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
