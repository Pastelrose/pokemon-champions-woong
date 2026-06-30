# Pokemon Champions 조회 웹 (Python / FastAPI)

DuckDB(pokemon_champions.duckdb)의 테이블을 조인해 보여주는 조회용 웹 페이지입니다.
나중에 스프링부트(MVC + Thymeleaf + MyBatis)로 이관하기 쉽도록, SQL은 queries.py에 모아두었습니다.

## 구성

- app.py: FastAPI 라우트 (스프링의 Controller에 해당) + 요청 로그 미들웨어
- queries.py: 모든 SQL (MyBatis 매퍼로 1:1 이관 대상)
- db.py: DuckDB 읽기 전용 연결 helper (메인 데이터 DB)
- logdb.py: 요청 로그 저장 (텍스트 파일)
- templates/: Jinja2 템플릿 (Thymeleaf로 이관 대상)
- static/style.css: 스타일

## 요청 로그

- 모든 HTTP 요청을 app.py의 미들웨어가 가로채 logdb.py를 통해 텍스트 파일로 기록합니다.
- 저장 위치: pokemon_web/logs/yyyymmdd.txt (날짜별 파일, 첫 요청 시 폴더/파일 자동 생성).
- 한 줄 형식: `요청시각 | 메서드 경로?쿼리 | status=상태코드 | 처리시간ms | ip=클라이언트IP | ua="유저에이전트"`
  - 예: `2026-06-30 07:03:54.378 | GET /pokemon?t1=드래곤&sort_col=스피드&sort_dir=desc | status=200 | 12.3ms | ip=127.0.0.1 | ua="..."`
- 쿼리스트링은 사람이 읽기 쉽게 URL 디코딩되어 기록됩니다.
- 로그 기록은 응답 생성 이후에 수행되고 전 과정이 try/except로 보호되어, 로그 저장이 실패해도 조회 결과에는 영향이 없습니다.
- logs 폴더는 .gitignore에 등록되어 버전 관리에서 제외됩니다.

## 관리자 전용 DB 재빌드 API (비공개)

CSV를 수정한 뒤, 서버를 끄지 않고 rebuild_db.sql을 실행해 pokemon_champions.duckdb를 갱신하는 비공개 엔드포인트입니다.

- 엔드포인트: POST /admin/rebuild-db
- 인증: 환경변수 ADMIN_TOKEN을 설정하고, 요청 헤더 X-Admin-Token 값이 일치해야 합니다.
  - 토큰 미설정/불일치 시 404로 응답해 엔드포인트 존재 자체를 숨깁니다.
  - 토큰을 헤더로 받으므로 요청 로그(쿼리스트링)에 남지 않습니다.
- 동작: rebuild_db.sql의 상대 CSV 경로를 데이터 폴더 절대경로로 바꿔 실행하고, 각 테이블 행수를 JSON으로 반환합니다.
- 재빌드 후에는 다음 요청부터 새 데이터가 자동 반영됩니다(서버 재시작 불필요).

토큰 설정(.env 사용):
- pokemon_web/.env.example 을 복사해 pokemon_web/.env 로 만들고 ADMIN_TOKEN 값을 채웁니다.
  - Windows: `copy .env.example .env`
- 서버 시작 시 app.py가 python-dotenv로 .env를 자동 로드합니다(OS 환경변수가 있으면 그쪽이 우선).
- .env 는 .gitignore에 등록되어 커밋되지 않습니다(.env.example 만 커밋).
- 값을 바꾸면 서버를 재시작해야 반영됩니다.

```
# pokemon_web/.env
ADMIN_TOKEN=원하는_비밀값
```

실행 및 호출:
```
uvicorn app:app --reload --port 8000
curl -X POST http://localhost:8000/admin/rebuild-db -H "X-Admin-Token: 원하는_비밀값"
```
응답 예: {"status":"ok","tables":{"pokemon":323,"moves":749, ...}}

주의: 재빌드는 DB를 쓰기 모드로 잠그므로, 그 짧은 순간 들어온 조회 요청은 일시적으로 지연/실패할 수 있습니다(쓰기 연결 획득은 재시도함). 트래픽이 한산할 때 호출하는 것을 권장합니다.

## 실행 방법

1. 의존성 설치
```
pip install -r requirements.txt
```

2. 실행 (pokemon_web 폴더 안에서)
```
uvicorn app:app --reload --port 8000
```

3. 브라우저에서 http://localhost:8000 접속

DB 경로는 코드에 하드코딩하지 않고, db.py가 자기 위치(__file__) 기준으로
../pokemon_champions_data/pokemon_champions.duckdb 를 자동으로 찾습니다.
따라서 프로젝트 폴더를 어디에 두든 그대로 동작합니다.
꼭 다른 위치의 DB를 쓰고 싶을 때만 환경변수 POKEMON_DB로 덮어쓸 수 있습니다(선택).

## 페이지

- /pokemon : 포켓몬 목록 (이름/타입 검색, 종족값 등 정렬)
- /pokemon/{id} : 상세 (특성·타입상성·배우는 기술 조인)
- /moves, /moves/{id} : 기술 목록/상세 (배우는 포켓몬 조인)
- /abilities, /abilities/{id} : 특성 목록/상세 (보유 포켓몬 조인)
- /items : 지닌물건 목록
- /types : 타입 상성표 매트릭스

## 스프링부트 이관 메모

- queries.py 의 각 함수 = MyBatis 매퍼의 select 한 개
- DuckDB 파일을 그대로 쓰려면 org.duckdb:duckdb_jdbc 드라이버 사용,
  또는 CSV를 MariaDB에 적재 후 기존 스택으로 조회
- 컬럼/테이블명이 한글이므로 매퍼에서 백틱 또는 따옴표 처리 주의
