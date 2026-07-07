# Pokemon Champions Tools 사이트 분석 및 데이터

출처: https://gamewith.ai/pokemon-champions (한국어 ko 페이지 기준)
수집 기준: 레귤레이션 M-A / M-B 로스터

## 사이트 구조 분석

GameWith가 만든 포켓몬 챔피언스용 공략 도구 모음 사이트이며, 10개 언어로 제공됩니다. 기술 스택은 Next.js 기반의 클라이언트 렌더링 SPA로 보이며, 목록 데이터는 페이지 진입 시 HTML에 함께 렌더링됩니다.

크게 세 영역으로 구성됩니다.

1. 데이터베이스: 사용률 랭킹, 포켓몬 DB, 기술 DB, 특성 DB, 지닌 도구 DB, 종족값 비교
2. 대전 도구: 육성 시뮬레이터, 데미지 일람표, 데미지 계산, 내구 조정, 스피드 비교
3. 기록: 티어표, 배틀 분석 노트, 대회 레이트 시뮬레이터

목록 페이지 특징:
- 포켓몬 DB: 100마리 단위 페이지네이션 (URL 쿼리 ?page=N), 총 4페이지 323마리
- 기술/특성/지닌물건 DB: 페이지네이션 없이 한 페이지에 전체 목록 표시, 필터는 클라이언트 측 동작
- 각 항목은 /pokemon/{id}, /moves/{id}, /abilities/{id}, /items/{id} 형태의 상세 페이지 ID를 가짐

## CSV 파일 설명

### pokemon_db.csv (323행)
컬럼: ID, 이름, 일본어이름, 영어이름, 타입1, 타입2, HP, 공격, 방어, 특공, 특방, 스피드, 종족값합계, 상세URL
- 종족값은 H/A/B/C/D/S 순서이며 합계는 직접 계산해 추가
- 특성은 별도의 pokemon_abilities.csv 연결 테이블로 분리(정규화)했습니다
- 사용률 순위는 시즌마다 바뀌므로 pokemon_usage_rank.csv로 분리했습니다

### pokemon_usage_rank.csv (323행)
컬럼: pokemon_id, 시즌, 기준일, 싱글순위, 더블순위
- 사용률 순위를 시즌(기간)별로 적재할 수 있는 별도 테이블
- pokemon_id = pokemon.ID, (pokemon_id, 시즌)이 사실상 키
- 조회 시 보통 가장 최근 기준일의 순위를 조인해서 사용
- 현재 데이터: 시즌 M-3 (기준일 2026-06-18) 한 건. 새 시즌은 행을 추가하면 됨

### pokemon_abilities.csv (664행)
컬럼: pokemon_id, slot, ability_id, ability_name
- 포켓몬과 특성의 다대다 연결 테이블
- pokemon_id = pokemon.ID, ability_id = abilities.ID
- slot은 특성 순서(1~3)이며, ability_name은 가독성을 위한 참고용 이름

### moves_db.csv (749행)
컬럼: ID, 기술명, 타입, 분류, 위력, 명중, PP, 성질, 대상, 효과, 상세URL
- 분류: 물리 / 특수 / 변화
- 위력, 명중이 없는 기술은 - 로 표기

### abilities_db.csv (313행)
컬럼: ID, 특성명, 효과, 상세URL

### items_db.csv (148행)
컬럼: ID, 이름, 효과, 입수방법, 이미지URL, 상세URL

### pokemon_moves.csv (20,416행)
컬럼: pokemon_id, move_id, pokemon_name, move_name
- 포켓몬이 배울 수 있는 기술(러닝셋)의 다대다 연결 테이블
- 각 포켓몬 상세 페이지의 "배우는 기술" 표에서 수집
- pokemon_id = pokemon.ID, move_id = moves.ID
- 323마리 전체, 사용된 고유 기술 496종, 포켓몬당 평균 약 63개(최소 1, 최대 105)

### type_chart.csv (324행)
컬럼: 공격타입, 방어타입, 배수
- 18개 타입 간 모든 조합(18x18)의 공격 효과 배수
- 배수: 0(효과 없음/면역), 0.5(효과가 별로), 1(보통), 2(효과가 굉장함)
- 표준 상성표 기준 (페어리 포함 9세대)

### type_chart_matrix.csv (사람이 보기 쉬운 표 형태)
- 행 = 공격타입, 열 = 방어타입, 값 = 배수
- type_chart.csv와 동일한 내용을 행렬로 표현한 참고용 파일

## 참고
- 모든 텍스트는 한국어 페이지 기준이며, 일본어 이름은 포켓몬 DB에만 포함했습니다.
- 인코딩은 UTF-8 (BOM 포함)으로, Excel에서 바로 열어도 한글이 깨지지 않습니다.
