# DuckDB로 데이터 보기

파일: pokemon_champions.duckdb
테이블: pokemon(323), moves(749), abilities(313), items(148), pokemon_abilities(664)

## 여는 방법

### 1) DuckDB CLI
```
duckdb pokemon_champions.duckdb
```
실행 후 SQL 입력. 종료는 .quit

### 2) DuckDB UI (브라우저 화면)
```
duckdb -ui pokemon_champions.duckdb
```

### 3) Python
```python
import duckdb
con = duckdb.connect("pokemon_champions.duckdb", read_only=True)
print(con.sql("SELECT * FROM pokemon LIMIT 10"))
```

### CSV를 직접 읽기 (DB 파일 없이)
```sql
SELECT * FROM read_csv_auto('pokemon_db.csv', header=true);
```

## 테이블 구조

- pokemon: ID, 이름, 일본어이름, 타입1, 타입2, HP, 공격, 방어, 특공, 특방, 스피드, 종족값합계, 싱글순위, 더블순위, 상세URL
- moves: ID, 기술명, 타입, 분류, 위력, 명중, PP, 성질, 대상, 효과, 상세URL
- abilities: ID, 특성명, 효과, 상세URL
- items: ID, 이름, 효과, 입수방법, 이미지URL, 상세URL
- pokemon_abilities: pokemon_id, slot, ability_id, ability_name  (포켓몬-특성 연결 테이블)
- type_chart: 공격타입, 방어타입, 배수  (타입 상성표, 324행)
- pokemon_moves: pokemon_id, move_id, pokemon_name, move_name  (포켓몬-기술 러닝셋 연결 테이블, 20,416행)
- pokemon_usage_rank: pokemon_id, 시즌, 기준일, 싱글순위, 더블순위  (시즌별 사용률 순위, 323행)

참고: pokemon 테이블에는 더 이상 싱글순위/더블순위가 없습니다. 순위는 시즌마다 바뀌므로 pokemon_usage_rank로 분리했고, 보통 가장 최근 기준일을 조인해서 봅니다.

```sql
-- 최신 기준일의 순위를 조인해 조회
SELECT p.이름, ur.싱글순위, ur.더블순위
FROM pokemon p
LEFT JOIN (
  SELECT pokemon_id, 싱글순위, 더블순위 FROM pokemon_usage_rank
  WHERE 기준일 = (SELECT max(기준일) FROM pokemon_usage_rank)
) ur ON ur.pokemon_id = p.ID
ORDER BY ur.싱글순위 NULLS LAST;
```
- pokemon_type_effectiveness (뷰): 공격타입, pokemon_id, 포켓몬, 타입1, 타입2, 최종배수  (듀얼타입까지 곱한 최종 배수)

참고: 포켓몬의 특성은 더 이상 pokemon 테이블에 문자열로 저장하지 않고, pokemon_abilities 연결 테이블로 정규화했습니다. slot은 특성 순서(1~3)입니다. pokemon_id는 pokemon.ID, ability_id는 abilities.ID와 연결됩니다.

## 예시 쿼리

종족값합계 상위 10
```sql
SELECT 이름, 타입1, 타입2, 종족값합계, 싱글순위
FROM pokemon ORDER BY 종족값합계 DESC LIMIT 10;
```

싱글 사용률 상위 20
```sql
SELECT 싱글순위, 이름, 타입1, 타입2, 종족값합계
FROM pokemon WHERE 싱글순위 > 0 ORDER BY 싱글순위 LIMIT 20;
```

타입1 분포
```sql
SELECT 타입1, count(*) AS 수 FROM pokemon GROUP BY 타입1 ORDER BY 수 DESC;
```

위력이 가장 높은 물리 기술
```sql
SELECT 기술명, 타입, TRY_CAST(위력 AS INT) AS 위력
FROM moves WHERE 분류 = '물리' AND TRY_CAST(위력 AS INT) IS NOT NULL
ORDER BY 위력 DESC LIMIT 10;
```

특정 타입 기술 검색
```sql
SELECT 기술명, 분류, 위력, 명중, 효과 FROM moves WHERE 타입 = '불꽃';
```

특성 효과 키워드 검색
```sql
SELECT 특성명, 효과 FROM abilities WHERE 효과 LIKE '%화상%';
```

특정 특성을 가진 포켓몬 검색 (연결 테이블 활용)
```sql
SELECT p.이름, p.타입1, p.타입2
FROM pokemon p
JOIN pokemon_abilities pa ON p.ID = pa.pokemon_id
JOIN abilities a ON pa.ability_id = a.ID
WHERE a.특성명 = '엽록소';
```

포켓몬별 특성 목록 한 줄로 보기 (예전 문자열 형태처럼 복원)
```sql
SELECT p.이름,
       string_agg(a.특성명, ' / ' ORDER BY pa.slot) AS 특성목록
FROM pokemon p
JOIN pokemon_abilities pa ON p.ID = pa.pokemon_id
JOIN abilities a ON pa.ability_id = a.ID
GROUP BY p.이름;
```

특성 효과로 포켓몬 검색 (특성-효과까지 한 번에)
```sql
SELECT DISTINCT p.이름, a.특성명, a.효과
FROM pokemon p
JOIN pokemon_abilities pa ON p.ID = pa.pokemon_id
JOIN abilities a ON pa.ability_id = a.ID
WHERE a.효과 LIKE '%날씨%';
```

참고: 위력, 명중 컬럼은 값이 없을 때 - 로 저장되어 있어 숫자 비교 시 TRY_CAST 를 사용합니다.

## 타입 상성 쿼리

불꽃 공격이 효과가 굉장한(2배) 타입
```sql
SELECT 방어타입 FROM type_chart WHERE 공격타입='불꽃' AND 배수=2;
```

특정 포켓몬에게 효과가 굉장한(2배 이상) 공격타입 (듀얼타입 반영)
```sql
SELECT 공격타입, 최종배수
FROM pokemon_type_effectiveness
WHERE 포켓몬='한카리아스' AND 최종배수>=2
ORDER BY 최종배수 DESC;
```

4배 약점이 존재하는 포켓몬 목록
```sql
SELECT DISTINCT 포켓몬, 타입1, 타입2, 공격타입, 최종배수
FROM pokemon_type_effectiveness
WHERE 최종배수=4 ORDER BY 포켓몬;
```

특정 타입 공격을 무효화(0배)하는 포켓몬
```sql
SELECT 포켓몬, 타입1, 타입2
FROM pokemon_type_effectiveness
WHERE 공격타입='땅' AND 최종배수=0;
```

## 러닝셋(배우는 기술) 쿼리

특정 포켓몬이 배우는 기술 목록
```sql
SELECT mv.기술명, mv.타입, mv.분류, mv.위력
FROM pokemon_moves pm
JOIN moves mv ON pm.move_id = mv.ID
WHERE pm.pokemon_id = 554
ORDER BY mv.타입, TRY_CAST(mv.위력 AS INT) DESC NULLS LAST;
```

특정 기술을 배우는 포켓몬 검색
```sql
SELECT p.이름, p.타입1, p.타입2
FROM pokemon_moves pm
JOIN pokemon p ON pm.pokemon_id = p.ID
JOIN moves mv ON pm.move_id = mv.ID
WHERE mv.기술명 = '칼춤';
```

얼음 기술을 배우면서 얼음이 약점인 포켓몬 (자체 약점 보완 검색 예시)
```sql
SELECT DISTINCT p.이름
FROM pokemon p
JOIN pokemon_moves pm ON p.ID = pm.pokemon_id
JOIN moves mv ON pm.move_id = mv.ID AND mv.타입='얼음'
JOIN pokemon_type_effectiveness e ON e.pokemon_id=p.ID AND e.공격타입='얼음'
WHERE e.최종배수 >= 2;
```

포켓몬이 배우는 기술을 한 줄로 나열
```sql
SELECT p.이름, string_agg(mv.기술명, ', ') AS 기술목록
FROM pokemon p
JOIN pokemon_moves pm ON p.ID = pm.pokemon_id
JOIN moves mv ON pm.move_id = mv.ID
GROUP BY p.이름;
```
