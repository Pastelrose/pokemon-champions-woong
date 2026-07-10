# -*- coding: utf-8 -*-
"""이전 CSV와 새 CSV를 비교해 변경 리포트를 만든다."""
import csv
import datetime
from pathlib import Path

from config import REPORT_DIR, CSV_FILES

# 파일별 키 컬럼 (이 키로 추가/삭제/변경을 판단)
KEYS = {
    "pokemon_db.csv": ["ID"],
    "moves_db.csv": ["ID"],
    "abilities_db.csv": ["ID"],
    "items_db.csv": ["ID"],
    "pokemon_abilities.csv": ["pokemon_id", "slot"],
    "pokemon_moves.csv": ["pokemon_id", "move_id"],
    "pokemon_usage_rank.csv": ["pokemon_id", "시즌"],
}
# 리포트에 이름을 보여줄 컬럼
LABELS = {
    "pokemon_db.csv": "이름",
    "moves_db.csv": "기술명",
    "abilities_db.csv": "특성명",
    "items_db.csv": "이름",
    "pokemon_abilities.csv": "ability_name",
    "pokemon_moves.csv": "move_name",
    "pokemon_usage_rank.csv": "기준일",
}
MAX_DETAIL = 50  # 파일당 상세 표시 최대 줄수


def _load(path, keys):
    if not Path(path).exists():
        return {}, []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        recs = {tuple(r[k] for k in keys): r for r in reader}
    return recs, header


def make_report(old_dir, new_dir, extra_lines=None):
    """비교 리포트 텍스트를 만들고 reports/날짜.txt로 저장. (경로, 요약문) 반환."""
    old_dir, new_dir = Path(old_dir), Path(new_dir)
    lines = ["갱신 리포트 " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""]
    if extra_lines:
        lines += list(extra_lines) + [""]
    summary = []

    for name in CSV_FILES:
        keys = KEYS[name]
        label = LABELS[name]
        old, _ = _load(old_dir / name, keys)
        new, _ = _load(new_dir / name, keys)
        added = [k for k in new if k not in old]
        removed = [k for k in old if k not in new]
        changed = [k for k in new if k in old and new[k] != old[k]]
        summary.append(f"{name}: 추가 {len(added)}, 삭제 {len(removed)}, 변경 {len(changed)}")
        lines.append(f"[{name}] 추가 {len(added)} / 삭제 {len(removed)} / 변경 {len(changed)}")

        def _label(recs, k):
            return recs[k].get(label, "")

        for title, ks, recs in (("추가", added, new), ("삭제", removed, old)):
            for k in ks[:MAX_DETAIL]:
                lines.append(f"  {title}: {'/'.join(k)} {_label(recs, k)}")
            if len(ks) > MAX_DETAIL:
                lines.append(f"  ... 외 {len(ks) - MAX_DETAIL}건")
        for k in changed[:MAX_DETAIL]:
            diffs = [f"{c}: {old[k].get(c,'')} -> {v}"
                     for c, v in new[k].items() if old[k].get(c, "") != v]
            lines.append(f"  변경: {'/'.join(k)} {_label(new, k)} ({'; '.join(diffs[:4])})")
        if len(changed) > MAX_DETAIL:
            lines.append(f"  ... 외 {len(changed) - MAX_DETAIL}건")
        lines.append("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / (datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path, " | ".join(summary)
