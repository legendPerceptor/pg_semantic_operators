-- ============================================================
-- Batch Processing Test Script for pg_semantic_operators
-- 使用 Movies 数据集测试批量处理功能
-- ============================================================

\timing on

\echo '========================================='
\echo '1. 准备测试数据'
\echo '========================================='

DROP TABLE IF EXISTS test_movies;
CREATE TEMP TABLE test_movies AS
SELECT id, title, audience_score, genre, director, rating
FROM movies
WHERE audience_score IS NOT NULL
  AND genre IS NOT NULL
LIMIT 20;

SELECT '测试数据量: ' || COUNT(*) || ' 部电影' FROM test_movies;

\echo ''
\echo '========================================='
\echo '2. 测试 ai_filter_batch - 批量语义过滤'
\echo '========================================='
\echo '测试条件: 评分高于 70 分的电影'

SELECT ai_filter_batch(
    'minimax',
    '评分高于70分',
    (SELECT jsonb_agg(jsonb_build_object(
        'title', title,
        'audience_score', audience_score,
        'genre', genre
    )) FROM test_movies)
) AS batch_results;

\echo ''
\echo '========================================='
\echo '3. 测试 ai_query_batch - 批量 SQL 生成'
\echo '========================================='

SELECT ai_query_batch(
    'minimax',
    '["查询所有评分高于80分的电影", "统计每个类型的电影数量", "找出评分最高的10部电影"]'::jsonb,
    '表: movies(id, title, audience_score, genre, director, rating)'
) AS generated_sql;

\echo ''
\echo '========================================='
\echo '4. 使用 jsonb_to_recordset 解析批量结果'
\echo '========================================='

WITH batch_result AS (
    SELECT * FROM jsonb_to_recordset(
        ai_filter_batch(
            'minimax',
            '是一部喜剧类型的电影',
            (SELECT jsonb_agg(jsonb_build_object(
                'title', title,
                'genre', genre
            )) FROM test_movies)
        )
    ) AS t("index" int, result boolean)
),
indexed_movies AS (
    SELECT
        ROW_NUMBER() OVER () - 1 AS idx,
        title,
        genre
    FROM test_movies
)
SELECT
    im.title,
    im.genre,
    br.result AS is_comedy
FROM indexed_movies im
LEFT JOIN batch_result br ON im.idx = br."index"
ORDER BY im.idx;

\echo ''
\echo '========================================='
\echo '5. 测试不同批量大小'
\echo '========================================='

\echo '--- 5.1 批量大小 = 5 ---'
SELECT ai_filter_batch(
    'minimax',
    '评分高于60分',
    (SELECT jsonb_agg(jsonb_build_object('audience_score', audience_score)) FROM test_movies LIMIT 15),
    5
) IS NOT NULL AS test_passed;

\echo '--- 5.2 批量大小 = 10 (默认) ---'
SELECT ai_filter_batch(
    'minimax',
    '评分高于60分',
    (SELECT jsonb_agg(jsonb_build_object('audience_score', audience_score)) FROM test_movies LIMIT 15),
    10
) IS NOT NULL AS test_passed;

\echo ''
\echo '========================================='
\echo '6. 实际应用示例: 批量筛选高评分电影'
\echo '========================================='

WITH batch_filter AS (
    SELECT * FROM jsonb_to_recordset(
        ai_filter_batch(
            'minimax',
            '是一部值得推荐的高分电影',
            (SELECT jsonb_agg(jsonb_build_object(
                'title', title,
                'audience_score', audience_score,
                'genre', genre
            )) FROM test_movies WHERE audience_score > 80 LIMIT 10)
        )
    ) AS t("index" int, result boolean)
),
indexed_source AS (
    SELECT
        ROW_NUMBER() OVER () - 1 AS idx,
        title,
        audience_score,
        genre
    FROM movies WHERE audience_score > 80 LIMIT 10
)
SELECT
    src.title,
    src.audience_score,
    src.genre,
    CASE WHEN flt.result THEN '✓ 推荐' ELSE '✗ 不推荐' END AS ai_judgment
FROM indexed_source src
LEFT JOIN batch_filter flt ON src.idx = flt."index"
ORDER BY src.idx;

\echo ''
\echo '========================================='
\echo '测试完成!'
\echo '========================================='
