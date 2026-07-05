# Pokemon Champions 조회 프로젝트

포켓몬 챔피언스(Pokemon Champions) 대전 데이터를 수집해 로컬 DuckDB에 적재하고,
웹 화면으로 조회하는 프로젝트입니다.

데이터 출처: https://gamewith.ai/pokemon-champions (한국어 페이지 기준)

## 폴더 구조

```
pokemon-champions-woong/
├── pokemon_champions_data/   데이터 (CSV 원본 + DuckDB + 재빌드 SQL)
│   ├── *.csv                 수집한 원본 데이터
│   ├── pokemon_champions.duckdb   조회용 DB (CSV로부터 생성)
│   ├── rebuild_db.sql        CSV -> DuckDB 재생성 스크립트
│   └── README.md             데이터 상세 설명 (테이블/컬럼 정의)
└── pokemon_web/              조회 웹 (Python / FastAPI)
    ├── app.py                라우트 + 요청 로그 미들웨어
    ├── queries.py            모든 SQL (MyBatis 이관 대상)
    ├── db.py                 DuckDB 읽기 전용 연결 helper
    ├── logdb.py              요청 로그 (텍스트 파일)
    ├── rebuild.py            관리자용 DB 재빌드 모듈
    ├── templates/            Jinja2 템플릿
    ├── tests/                pytest 테스트 (이관 시 결과 비교 기준)
    └── README.md             웹 상세 설명 (실행 방법, 페이지, 관리자 API)
```

## 빠른 시작

```
cd pokemon_web
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8000
```

브라우저에서 http://localhost:8000 접속.

(Windows에서 `pip`으로 설치한 실행 파일(Scripts) 경로가 PATH에 없으면
`uvicorn` 명령을 바로 찾지 못할 수 있습니다. 이때는 위처럼 `python -m uvicorn`으로 실행하세요.)

DB 파일이 저장소에 포함되어 있어 별도 준비 없이 바로 실행됩니다.
CSV를 수정한 경우에만 rebuild_db.sql로 DB를 재생성하면 됩니다
(방법은 pokemon_champions_data/README.md와 pokemon_web/README.md 참고).

## 테스트

```
cd pokemon_web
pytest
```

queries.py의 조회 결과를 현재 데이터 기준 기대값과 비교합니다.
스프링부트(MyBatis) 이관 후 동일 SQL의 결과 검증 기준으로도 사용합니다.

## 향후 계획

- 스프링부트(MVC + Thymeleaf + MyBatis)로 이관 예정
- 이관을 쉽게 하기 위해 SQL은 queries.py 한 파일에 모아둠
- 상세 메모는 pokemon_web/README.md의 "스프링부트 이관 메모" 참고
