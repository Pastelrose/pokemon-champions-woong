# -*- coding: utf-8 -*-
"""파싱 결과 -> 기존 스키마 그대로의 CSV 생성 (utf-8-sig, BOM 포함)."""
import csv
import datetime
from pathlib import Path

from config import BASE_URL, LOCALE, NEW_CSV_DIR


def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _detail_url(kind, id_):
    return f"{BASE_URL}/{LOCALE}/{kind}/{id_}"


def build_pokemon_csv(pokemon_rows, en_names):
    """pokemon_db.csv 생성."""
    header = ["ID","도감번호","이름","일본어이름","영어이름","이미지URL","타입1","타입2",
              "HP","공격","방어","특공","특방","스피드","종족값합계","상세URL"]
    rows = []
    for p in sorted(pokemon_rows, key=lambda x: x["ID"]):
        types = p["타입리스트"]
        total = p["HP"]+p["공격"]+p["방어"]+p["특공"]+p["특방"]+p["스피드"]
        rows.append([
            p["ID"], p["도감번호"] if p["도감번호"] is not None else "",
            p["이름"], p["일본어이름"], en_names.get(p["ID"], ""),
            p["이미지URL"],
            types[0] if len(types) > 0 else "",
            types[1] if len(types) > 1 else "",
            p["HP"], p["공격"], p["방어"], p["특공"], p["특방"], p["스피드"],
            total, _detail_url("pokemon", p["ID"]),
        ])
    _write(NEW_CSV_DIR / "pokemon_db.csv", header, rows)
    return len(rows)


def build_moves_csv(move_rows):
    header = ["ID","기술명","타입","분류","위력","명중","PP","성질","대상","효과","상세URL"]
    rows = [[m["ID"], m["기술명"], m["타입"], m["분류"], m["위력"], m["명중"],
             m["PP"], m["성질"], m["대상"], m["효과"], _detail_url("moves", m["ID"])]
            for m in sorted(move_rows, key=lambda x: x["ID"])]
    _write(NEW_CSV_DIR / "moves_db.csv", header, rows)
    return len(rows)


def build_abilities_csv(ability_rows):
    header = ["ID","특성명","효과","상세URL"]
    rows = [[a["ID"], a["특성명"], a["효과"], _detail_url("abilities", a["ID"])]
            for a in sorted(ability_rows, key=lambda x: x["ID"])]
    _write(NEW_CSV_DIR / "abilities_db.csv", header, rows)
    return len(rows)


def build_items_csv(item_rows):
    header = ["ID","이름","효과","입수방법","이미지URL","상세URL"]
    rows = [[i["ID"], i["이름"], i["효과"], i["입수방법"], i["이미지URL"],
             _detail_url("items", i["ID"])]
            for i in sorted(item_rows, key=lambda x: x["ID"])]
    _write(NEW_CSV_DIR / "items_db.csv", header, rows)
    return len(rows)


def build_pokemon_abilities_csv(pokemon_rows, ability_rows):
    """목록 페이지의 특성 이름을 abilities ID로 매핑해 연결 테이블 생성."""
    name_to_id = {a["특성명"]: a["ID"] for a in ability_rows}
    header = ["pokemon_id","slot","ability_id","ability_name"]
    rows, missing = [], []
    for p in sorted(pokemon_rows, key=lambda x: x["ID"]):
        for slot, name in enumerate(p["특성명리스트"], start=1):
            aid = name_to_id.get(name)
            if aid is None:
                missing.append((p["ID"], p["이름"], name))
                continue
            rows.append([p["ID"], slot, aid, name])
    _write(NEW_CSV_DIR / "pokemon_abilities.csv", header, rows)
    return len(rows), missing


def build_pokemon_moves_csv(learnsets, pokemon_rows):
    """learnsets: {pokemon_id: [(move_id, move_name)]}"""
    id_to_name = {p["ID"]: p["이름"] for p in pokemon_rows}
    header = ["pokemon_id","move_id","pokemon_name","move_name"]
    rows = []
    for pid in sorted(learnsets):
        for mid, mname in learnsets[pid]:
            rows.append([pid, mid, id_to_name.get(pid, ""), mname])
    _write(NEW_CSV_DIR / "pokemon_moves.csv", header, rows)
    return len(rows)


def build_usage_rank_csv(pokemon_rows, season, base_date, old_csv_path):
    """pokemon_usage_rank.csv 생성.

    기존 CSV에서 '다른 시즌' 행은 그대로 보존하고(이력 유지),
    현재 시즌 행만 새 순위로 교체한다.
    """
    if base_date is None:
        base_date = datetime.date.today().isoformat()
    header = ["pokemon_id","시즌","기준일","싱글순위","더블순위"]
    rows = []
    old = Path(old_csv_path)
    if old.exists():
        with open(old, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["시즌"] != season:  # 과거 시즌 이력 보존
                    rows.append([r["pokemon_id"], r["시즌"], r["기준일"],
                                 r["싱글순위"], r["더블순위"]])
    for p in sorted(pokemon_rows, key=lambda x: x["ID"]):
        rows.append([p["ID"], season, base_date,
                     p["싱글순위"] if p["싱글순위"] is not None else "",
                     p["더블순위"] if p["더블순위"] is not None else ""])
    _write(NEW_CSV_DIR / "pokemon_usage_rank.csv", header, rows)
    return len(rows)
