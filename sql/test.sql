-- 测试 PostgreSQL 语义算子扩展
DROP TABLE IF EXISTS orders;
-- 1. 创建测试表
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    amount NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 插入测试数据
INSERT INTO orders (customer_name, amount, status) VALUES
    ('张三', 500, '进行中'),
    ('李四', 1500, '已完成'),
    ('王五', 2000, '已完成'),
    ('赵六', 800, '已取消'),
    ('钱七', 3000, '已完成');

-- 2. 测试 list_models
SELECT list_models();

-- 3. 测试 ai_query (需要配置 API Key)
SELECT ai_query('minimax', '找出金额大于1000的订单');

-- 4. 测试 ai_filter (需要配置 API Key)
SELECT * FROM orders
WHERE ai_filter('minimax', '金额大于1000且状态是已完成',
                jsonb_build_object('customer_name', customer_name, 'amount', amount, 'status', status));

-- 5. 获取 schema 信息
SELECT get_schema_info();

DROP TABLE orders;
