# Pokemon Champions 데이터 자동 갱신 (pokemon_updater)

gamewith.ai/pokemon-champions (ko) 페이지를 주기적으로 수집해
pokemon_champions_data/의 CSV와 DuckDB를 자동 갱신하는 배치 프로젝트입니다.
AI 없이 순수 코드(HTML 파싱)로만 동작하며, 리눅스 cron 실행을 전제로 합니다.

## 동작 원리

사이트는 Next.js 기반이지만 목록 데이터가 HTML 표(table)로 함께 렌더링되므로,
requests + BeautifulSoup으로 표를 읽어 기존 CSV 스키마 그대로 재생성합니다.
웹 조회 프로젝트(pokemon_web)의 코드는 전혀 수정할 필요가 없습니다.

파이프라인은 5단계입니다.

1. 수집: 포켓몬 목록(페이지네이션), 기술/특성/지닌물건 목록, 포켓몬 상세(배우는 기술),
   영어 이름(en 로케일 목록), 시즌 정보(usage-ranking)
2. 변환: work/new_csv/ 에 기존과 동일한 스키마의 CSV 생성 (utf-8-sig)
3. 검증: 헤더 일치, 행수 급감(기본 90% 미만이면 중단), 타입 값, 종족값 합계,
   연결 테이블 참조 무결성 등 검사. 하나라도 실패하면 적재하지 않고 종료 코드 1
4. 백업/적재: 기존 CSV+DB를 backup/타임스탬프/ 에 복사한 뒤 새 CSV로 교체하고
   rebuild_db.sql로 DuckDB 재빌드. 실패 시 백업으로 자동 복원. 백업은 최근 10개 보관
5. 리포트: 추가/삭제/변경 내역을 reports/날짜.txt 로 저장

수집 예절: 요청 간격 기본 1.5초, 식별 가능한 User-Agent 사용.
전체 갱신은 약 330여 페이지를 읽으므로 10분 정도 걸립니다.
운영 전에 사이트 이용약관과 robots.txt를 확인하세요.

## 파일 구성

- config.py: 경로, 요청 간격, 검증 기준 등 설정
- fetch.py: HTTP 수집기 (간격 준수, 재시도)
- parsers.py: HTML 파서 (사이트 구조 변경 시 이 파일만 수정)
- build_csv.py: 파싱 결과를 CSV로 변환
- validate.py: 적재 전 검증 (안전장치)
- deploy.py: 백업, CSV 교체, DuckDB 재빌드, 복원
- report.py: 변경 diff 리포트
- update_all.py: 전체 갱신 파이프라인
- update_rank.py: 사용률 순위만 빠르게 갱신 (목록 페이지만 사용, 1분 이내)
- run_update.sh / run_rank.sh: cron용 래퍼 (flock 중복 방지 + 날짜별 로그)

type_chart.csv는 게임 규칙이라 변하지 않으므로 갱신 대상이 아닙니다.

## 설치 (리눅스)

```
cd pokemon_updater
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

venv를 쓰는 경우 cron 래퍼가 참조하도록 PYTHON 환경변수를 지정하거나,
run_update.sh 안의 PY 기본값을 venv/bin/python3 으로 바꿔주세요.

## 처음 한 번은 반드시 수동 점검

사이트 실측 구조로 파서를 작성했지만, 처음 운영 서버에서 돌릴 때는
아래 순서로 점검 후 cron에 등록하는 것을 권장합니다.

```
# 1) 대표 페이지 원본 HTML 저장 (파서가 이상할 때 구조 확인용)
python3 update_all.py --probe

# 2) 상세 5건만 수집해 파서 동작 확인
python3 update_all.py --limit 5 --dry-run

# 3) 전체 수집 + 검증 + 리포트 (적재는 안 함)
python3 update_all.py --dry-run
# reports/ 폴더의 리포트에서 추가/삭제/변경이 상식적인지 확인

# 4) 실제 적용
python3 update_all.py
```

## cron 등록 (리눅스)

crontab -e 로 아래를 추가합니다. 경로는 실제 설치 위치로 바꿔주세요.

```
# 매주 월요일 05:00 전체 갱신 (신규 포켓몬/기술/도구 반영)
0 5 * * 1 /home/user/pokemon-champions-woong/pokemon_updater/run_update.sh

# 매일 05:30 사용률 순위만 갱신
30 5 * * * /home/user/pokemon-champions-woong/pokemon_updater/run_rank.sh
```

- 로그: pokemon_updater/logs/full_YYYYMMDD.log, rank_YYYYMMDD.log
- 리포트: pokemon_updater/reports/YYYYMMDD_HHMMSS.txt
- 백업: pokemon_updater/backup/YYYYMMDD_HHMMSS/ (최근 10개 자동 보관)
- flock으로 같은 작업이 겹쳐 실행되지 않게 막습니다

## 실패 시 동작

- 수집/파싱이 깨지면: 검증 단계에서 걸러져 기존 데이터가 그대로 유지되고,
  종료 코드 1과 함께 로그/리포트에 원인이 남습니다
- 적재 중 오류가 나면: 직전 백업으로 자동 복원됩니다
- 수동 복원: backup/원하는시점/ 의 CSV들을 pokemon_champions_data/ 로 복사한 뒤
  전체 갱신을 다시 돌리거나 웹의 관리자 재빌드 API를 호출하면 됩니다

## 서비스 반영

DuckDB 재빌드가 끝나면 웹(pokemon_web)은 다음 요청부터 새 데이터를 자동으로
읽습니다(재시작 불필요). 재빌드 순간에는 짧은 쓰기 잠금이 걸리므로
새벽 등 한산한 시간에 cron을 걸어두는 것이 좋습니다.

## 한계와 대응

사이트가 표 구조나 URL 체계를 크게 바꾸면 parsers.py를 수정해야 합니다.
그 경우에도 검증 단계 덕분에 잘못된 데이터가 서비스에 올라가지는 않으며,
update_all.py --probe 로 저장한 원본 HTML을 보고 선택자를 고치면 됩니다.
