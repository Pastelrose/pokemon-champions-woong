# -*- coding: utf-8 -*-
"""새 CSV를 적재 전에 기계적으로 검사하는 안전장치.

하나라도 실패하면 갱신을 중단하고 기존 데이터를 유지한다.
사이트 구조가 바뀌어 파싱이 깨진 경우도 여기서 걸러진다.
"""
import csv
from pathlib import Path

from config import TYPES, MIN_ROW_RATIO, CSV_FILES

EXPECTED_HEADERS = {
    "pokemon_db.csv": ["ID","도감번호","이름","일본어이름","영어이름","이미지URL","타입1","타입2",
                       "HP","공격","방어","특공","특방","스피드","종족값합계","상세URL"],
    "moves_db.csv": ["ID","기술명","타입","분류","위력","명중","PP","성질","대상","효과","상세URL"],
    "abilities_db.csv": ["ID","특성명","효과","상세URL"],
    "items_db.csv": ["ID","이름","효과","입수방법","이미지URL","상세URL"],
    "pokemon_abilities.csv": ["pokemon_id","slot","ability_id","ability_name"],
    "pokemon_moves.csv": ["pokemon_id","move_id","pokemon_name","move_name"],
    "pokemon_usage_rank.csv": ["pokemon_id","시즌","기준일","싱글순위","더블순위"],
}

_TYPE_SET = set(TYPES)


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def validate_all(new_dir, old_dir):
    """new_dir의 CSV들을 검사. 문제 목록(문자열 리스트)을 반환. 비어 있으면 통과."""
    new_dir, old_dir = Path(new_dir), Path(old_dir)
    errors = []
    data = {}

    for name in CSV_FILES:
        path = new_dir / name
        if not path.exists():
            errors.append(f"{name}: 파일이 생성되지 않았습니다")
            continue
        header, rows = _read(path)
        if header != EXPECTED_HEADERS[name]:
            errors.append(f"{name}: 헤더가 예상과 다릅니다 -> {header}")
            continue
        data[name] = (header, rows)

        # 행수 급감 방지
        old_path = old_dir / name
        if old_path.exists():
            old_count = len(_read(old_path)[1])
            if old_count > 0 and len(rows) < old_count * MIN_ROW_RATIO:
                errors.append(f"{name}: 행수 급감 {old_count} -> {len(rows)} "
                              f"(기준 {MIN_ROW_RATIO:.0%} 미만이면 중단)")
    if errors:
        return errors

    # ---- pokemon_db ----
    _, prows = data["pokemon_db.csv"]
    pids = set()
    for r in prows:
        rec = dict(zip(EXPECTED_HEADERS["pokemon_db.csv"], r))
        pid = rec["ID"]
        if pid in pids:
            errors.append(f"pokemon_db: ID 중복 {pid}")
        pids.add(pid)
        if not rec["이름"]:
            errors.append(f"pokemon_db: ID {pid} 이름 없음")
        if rec["타입1"] not in _TYPE_SET:
            errors.append(f"pokemon_db: ID {pid} 타입1 이상 '{rec['타입1']}'")
        if rec["타입2"] and rec["타입2"] not in _TYPE_SET:
            errors.append(f"pokemon_db: ID {pid} 타입2 이상 '{rec['타입2']}'")
        try:
            stats = [int(rec[k]) for k in ["HP","공격","방어","특공","특방","스피드"]]
            if not all(1 <= s <= 255 for s in stats):
                errors.append(f"pokemon_db: ID {pid} 종족값 범위 이상 {stats}")
            if int(rec["종족값합계"]) != sum(stats):
                errors.append(f"pokemon_db: ID {pid} 종족값합계 불일치")
        except ValueError:
            errors.append(f"pokemon_db: ID {pid} 종족값이 숫자가 아님")

    # ---- moves_db ----
    _, mrows = data["moves_db.csv"]
    mids = set()
    for r in mrows:
        rec = dict(zip(EXPECTED_HEADERS["moves_db.csv"], r))
        mid = rec["ID"]
        if mid in mids:
            errors.append(f"moves_db: ID 중복 {mid}")
        mids.add(mid)
        if rec["타입"] not in _TYPE_SET:
            errors.append(f"moves_db: ID {mid} 타입 이상 '{rec['타입']}'")
        if rec["분류"] not in ("물리", "특수", "변화"):
            errors.append(f"moves_db: ID {mid} 분류 이상 '{rec['분류']}'")
        for k in ("위력", "명중", "PP"):
            if rec[k] and not rec[k].isdigit():
                errors.append(f"moves_db: ID {mid} {k} 숫자 아님 '{rec[k]}'")

    # ---- abilities / items ----
    aids = {dict(zip(EXPECTED_HEADERS["abilities_db.csv"], r))["ID"]
            for r in data["abilities_db.csv"][1]}
    for r in data["abilities_db.csv"][1]:
        rec = dict(zip(EXPECTED_HEADERS["abilities_db.csv"], r))
        if not rec["특성명"]:
            errors.append(f"abilities_db: ID {rec['ID']} 특성명 없음")
    for r in data["items_db.csv"][1]:
        rec = dict(zip(EXPECTED_HEADERS["items_db.csv"], r))
        if not rec["이름"]:
            errors.append(f"items_db: ID {rec['ID']} 이름 없음")

    # ---- 연결 테이블 FK ----
    for r in data["pokemon_abilities.csv"][1]:
        rec = dict(zip(EXPECTED_HEADERS["pokemon_abilities.csv"], r))
        if rec["pokemon_id"] not in pids:
            errors.append(f"pokemon_abilities: 없는 pokemon_id {rec['pokemon_id']}")
        if rec["ability_id"] not in aids:
            errors.append(f"pokemon_abilities: 없는 ability_id {rec['ability_id']}")

    covered = set()
    for r in data["pokemon_moves.csv"][1]:
        rec = dict(zip(EXPECTED_HEADERS["pokemon_moves.csv"], r))
        if rec["pokemon_id"] not in pids:
            errors.append(f"pokemon_moves: 없는 pokemon_id {rec['pokemon_id']}")
        if rec["move_id"] not in mids:
            errors.append(f"pokemon_moves: 없는 move_id {rec['move_id']} ({rec['move_name']})")
        covered.add(rec["pokemon_id"])
    uncovered = pids - covered
    if len(uncovered) > len(pids) * 0.05:
        errors.append(f"pokemon_moves: 배우는 기술이 없는 포켓몬이 너무 많음 ({len(uncovered)}마리)")

    for r in data["pokemon_usage_rank.csv"][1]:
        rec = dict(zip(EXPECTED_HEADERS["pokemon_usage_rank.csv"], r))
        if rec["pokemon_id"] not in pids:
            errors.append(f"usage_rank: 없는 pokemon_id {rec['pokemon_id']}")
        if not rec["시즌"]:
            errors.append("usage_rank: 시즌 값 없음")

    # 같은 오류 메시지 폭주 방지
    return errors[:200]
