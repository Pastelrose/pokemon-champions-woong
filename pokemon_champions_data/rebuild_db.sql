-- pokemon_champions.duckdb 재생성 스크립트
-- 사용법(폴더 안에서): duckdb pokemon_champions.duckdb < rebuild_db.sql
-- (기존 DB 파일이 열려 있으면 먼저 닫아주세요)

DROP VIEW IF EXISTS pokemon_type_effectiveness;
DROP TABLE IF EXISTS pokemon;
DROP TABLE IF EXISTS moves;
DROP TABLE IF EXISTS abilities;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS pokemon_abilities;
DROP TABLE IF EXISTS type_chart;
DROP TABLE IF EXISTS pokemon_moves;
DROP TABLE IF EXISTS pokemon_usage_rank;

CREATE TABLE pokemon            AS SELECT * FROM read_csv_auto('pokemon_db.csv', header=true);
CREATE TABLE moves              AS SELECT * FROM read_csv_auto('moves_db.csv', header=true);
CREATE TABLE abilities          AS SELECT * FROM read_csv_auto('abilities_db.csv', header=true);
CREATE TABLE items              AS SELECT * FROM read_csv_auto('items_db.csv', header=true);
CREATE TABLE pokemon_abilities  AS SELECT * FROM read_csv_auto('pokemon_abilities.csv', header=true);
CREATE TABLE type_chart         AS SELECT * FROM read_csv_auto('type_chart.csv', header=true);
CREATE TABLE pokemon_moves      AS SELECT * FROM read_csv_auto('pokemon_moves.csv', header=true);
CREATE TABLE pokemon_usage_rank AS SELECT * FROM read_csv_auto('pokemon_usage_rank.csv', header=true);

-- 공격타입이 각 포켓몬(듀얼타입 포함)에게 주는 최종 배수 뷰
CREATE VIEW pokemon_type_effectiveness AS
SELECT atk.공격타입 AS 공격타입, p.ID AS pokemon_id, p.이름 AS 포켓몬,
       p.타입1, p.타입2,
       t1.배수 * COALESCE(t2.배수, 1.0) AS 최종배수
FROM pokemon p
CROSS JOIN (SELECT DISTINCT 공격타입 FROM type_chart) atk
JOIN type_chart t1 ON t1.공격타입=atk.공격타입 AND t1.방어타입=p.타입1
LEFT JOIN type_chart t2 ON t2.공격타입=atk.공격타입 AND t2.방어타입=p.타입2;

-- 확인
SELECT 'pokemon' AS t, count(*) FROM pokemon
UNION ALL SELECT 'moves', count(*) FROM moves
UNION ALL SELECT 'abilities', count(*) FROM abilities
UNION ALL SELECT 'items', count(*) FROM items
UNION ALL SELECT 'pokemon_abilities', count(*) FROM pokemon_abilities
UNION ALL SELECT 'type_chart', count(*) FROM type_chart
UNION ALL SELECT 'pokemon_moves', count(*) FROM pokemon_moves
UNION ALL SELECT 'pokemon_usage_rank', count(*) FROM pokemon_usage_rank;
