# Pokemon Champions 조회 웹 (Python / FastAPI)

DuckDB(pokemon_champions.duckdb)의 테이블을 조인해 보여주는 조회용 웹 페이지입니다.
나중에 스프링부트(MVC + Thymeleaf + MyBatis)로 이관하기 쉽도록, SQL은 queries.py에 모아두었습니다.

## 구성

- app.py: FastAPI 라우트 (스프링의 Controller에 해당)
- queries.py: 모든 SQL (MyBatis 매퍼로 1:1 이관 대상)
- db.py: DuckDB 읽기 전용 연결 helper
- templates/: Jinja2 템플릿 (Thymeleaf로 이관 대상)
- static/style.css: 스타일

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
