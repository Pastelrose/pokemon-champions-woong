# -*- coding: utf-8 -*-
"""갱신 프로젝트 공통 설정.

경로는 이 파일(__file__) 기준 상대 경로로 계산하므로,
프로젝트 폴더를 어디에 두든 그대로 동작한다.
환경변수로 일부 값을 덮어쓸 수 있다.
"""
import os
from pathlib import Path

# 수집 대상 사이트 (한국어 페이지 기준)
BASE_URL = "https://gamewith.ai/pokemon-champions"
LOCALE = "ko"           # 메인 수집 언어
LOCALE_EN = "en"        # 영어 이름 수집용

# 요청 예절: 요청 간 최소 간격(초), 타임아웃(초), User-Agent
REQUEST_DELAY_SEC = float(os.environ.get("UPDATER_DELAY", "1.5"))
TIMEOUT_SEC = 20
USER_AGENT = "pokemon-champions-db-updater/1.0 (personal data sync; contact: local)"

# 경로: pokemon_updater/ -> 프로젝트 루트 -> pokemon_champions_data/
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("UPDATER_DATA_DIR") or (ROOT / "pokemon_champions_data"))
DB_PATH = DATA_DIR / "pokemon_champions.duckdb"
SQL_PATH = DATA_DIR / "rebuild_db.sql"

# 작업 폴더 (새 CSV 임시 저장, 원본 HTML 캐시)
WORK_DIR = Path(__file__).resolve().parent / "work"
NEW_CSV_DIR = WORK_DIR / "new_csv"
HTML_DIR = WORK_DIR / "html"      # --probe 로 저장되는 원본 HTML

# 백업/리포트 폴더
BACKUP_DIR = Path(__file__).resolve().parent / "backup"
REPORT_DIR = Path(__file__).resolve().parent / "reports"

# 18개 타입 (검증에 사용)
TYPES = ["노말","불꽃","물","풀","전기","얼음","격투","독","땅","비행",
         "에스퍼","벌레","바위","고스트","드래곤","악","강철","페어리"]

# 검증: 새 데이터 행수가 기존의 이 비율 미만이면 갱신 중단 (수집 실패로 판단)
MIN_ROW_RATIO = float(os.environ.get("UPDATER_MIN_ROW_RATIO", "0.9"))

# 갱신 대상 CSV 파일명 (type_chart는 불변이므로 대상 아님)
CSV_FILES = [
    "pokemon_db.csv",
    "moves_db.csv",
    "abilities_db.csv",
    "items_db.csv",
    "pokemon_abilities.csv",
    "pokemon_moves.csv",
    "pokemon_usage_rank.csv",
]


def url(path, locale=LOCALE):
    return f"{BASE_URL}/{locale}{path}"
