# ai_query (NL2SQL) 算子改进计划

## 一、现状分析

当前 `ai_query` 的实现非常简单，本质上是一个 **单次 Prompt → LLM → 正则提取 SQL** 的端到端流程：

| 维度 | 现状 | 问题 |
|------|------|------|
| **Schema 注入** | `get_schema_info()` 仅查询 `information_schema` 的表名/列名/类型/nullable，以纯文本格式注入 | 缺少外键关系、列注释、示例值、索引信息，LLM 无法理解表间 JOIN 路径 |
| **Prompt 工程** | 单一 system prompt，无 few-shot 示例 | LLM 缺乏业务语义理解，对模糊术语（如"高价值"）无法准确映射 |
| **算子调用** | 生成的 SQL 只能使用标准 SQL 语法 | 无法调用项目自定义的 `ai_filter`、`ai_query` 等算子，丧失了语义算子的核心价值 |
| **错误修正** | 无 | 生成的 SQL 若语法错误或逻辑错误，直接返回错误结果 |
| **SQL 验证** | 无 | 不验证 SQL 语法正确性，不检查是否引用了不存在的表/列 |
| **候选选择** | 单次生成 | 无法通过多候选投票（self-consistency）提升准确率 |

## 二、改进方案：六阶段流水线架构

参考业界最新方案（CHASE-SQL、DIN-SQL、SQL-of-Thought、TailorSQL、BASE-SQL 等），结合本项目作为 PostgreSQL 扩展的特殊定位，设计如下改进架构：

```
用户自然语言
    │
    ▼
┌─────────────────────────────────┐
│ 阶段1: Schema Linking（模式链接） │  ← 新增：智能筛选相关表/列
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 阶段2: Prompt Engineering 增强   │  ← 改进：Few-shot + 算子注册 + DAIL表示
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 阶段3: SQL 生成（多候选）         │  ← 改进：Beam Search 生成多个候选
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 阶段4: SQL 验证与自修正           │  ← 新增：语法校验 + 执行反馈修正
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 阶段5: 候选选择（Self-Consistency）│ ← 新增：执行结果投票选最优
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 阶段6: 安全检查与输出             │  ← 新增：SQL 注入防护 + 危险操作过滤
└─────────────────────────────────┘
```

## 三、各阶段详细设计

### 阶段1: Schema Linking（模式链接）

**目标**：从全量 schema 中精准检索与用户问题相关的表和列，减少无关信息干扰。

**参考方案**：Context-Aware Bidirectional Retrieval (Nahid et al., 2025)、CHESS

**实现方案**：

1. **增强 `get_schema_info()`**：
   - 新增外键关系（`information_schema.table_constraints` + `key_column_usage`）
   - 新增列注释（`pg_description` 系统目录）
   - 新增每列的示例值（`SELECT DISTINCT col FROM table LIMIT 3`）
   - 新增索引信息

2. **新增 `get_relevant_schema()` 函数**：
   - **方案A（轻量级，推荐先实现）**：基于关键词匹配 + 语义相似度（调用 LLM 做表选择）
   - **方案B（进阶）**：双向检索——Table-First（先选表再选列）+ Column-First（先选列再选表），取并集
   - 输出：精简的 schema 描述，只包含相关表/列

**SQL 函数签名**：
```sql
-- 增强版 schema 信息
CREATE OR REPLACE FUNCTION get_schema_info_enhanced(
    include_examples BOOLEAN DEFAULT TRUE,
    include_foreign_keys BOOLEAN DEFAULT TRUE
)
RETURNS TEXT;

-- 基于问题的相关 schema 检索
CREATE OR REPLACE FUNCTION get_relevant_schema(
    model_name TEXT,
    question TEXT
)
RETURNS TEXT;
```

### 阶段2: Prompt Engineering 增强

**目标**：让 LLM 理解业务语义、掌握自定义算子用法、学习典型查询模式。

**参考方案**：DAIL-SQL（代码表示法）、Few-shot Prompting

**实现方案**：

1. **Schema 代码表示法（DAIL-SQL 风格）**：
   - 将 schema 从纯文本描述改为 `CREATE TABLE` DDL 语句格式，包含主键/外键约束
   - LLM 对代码的理解能力远强于自然语言描述

2. **算子注册表（Operator Registry）**：
   - 在 prompt 中注入当前数据库可用的自定义算子列表及其用法
   - 例如：`ai_filter(model, condition, row_data)` → "对每行数据做语义过滤"
   - 让 LLM 知道可以在 SQL 中调用这些算子

3. **Few-shot 示例库**：
   - 新增 `ai_query_examples` 表，存储 NL-SQL 对
   - 支持动态选择与当前问题最相似的示例（基于 embedding 或关键词匹配）
   - 用户可手动添加示例，也可从历史查询中自动学习

4. **领域知识注入**：
   - 新增 `ai_query_knowledge` 表，存储业务术语映射（如"高价值" → `amount > 1000`）
   - 在 prompt 中注入相关领域知识

**新增 SQL 函数**：
```sql
-- 管理 few-shot 示例
CREATE OR REPLACE FUNCTION ai_query_add_example(
    question TEXT,
    sql_query TEXT,
    description TEXT DEFAULT NULL
)
RETURNS VOID;

-- 管理领域知识
CREATE OR REPLACE FUNCTION ai_query_add_knowledge(
    term TEXT,
    definition TEXT
)
RETURNS VOID;
```

**新增存储表**：
```sql
CREATE TABLE IF NOT EXISTS ai_query_examples (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_query_knowledge (
    id SERIAL PRIMARY KEY,
    term TEXT UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 阶段3: SQL 生成（多候选）

**目标**：通过多路径生成提升召回率。

**参考方案**：BASE-SQL（Beam Search）、MCS-SQL（多路径生成）

**实现方案**：

1. **多候选生成**：
   - 新增 `num_candidates` 参数（默认 1，最大 5）
   - 通过不同的 prompt 变体（不同的 few-shot 示例、不同的 schema 表示顺序）生成多个候选 SQL
   - 可选：使用不同 temperature 参数增加多样性

2. **Chain-of-Thought 生成**：
   - 新增 `cot` 模式：让 LLM 先输出推理过程，再输出 SQL
   - 参考 DIN-SQL 的分解策略：先识别需要的表 → 再确定 JOIN 条件 → 最后生成完整 SQL

**增强后的函数签名**：
```sql
CREATE OR REPLACE FUNCTION ai_query(
    model_name TEXT,
    user_prompt TEXT,
    schema_info TEXT DEFAULT NULL,
    num_candidates INTEGER DEFAULT 1,
    use_cot BOOLEAN DEFAULT FALSE
)
RETURNS TEXT;
```

### 阶段4: SQL 验证与自修正

**目标**：确保生成的 SQL 语法正确且可执行，对错误 SQL 自动修正。

**参考方案**：CHESS（执行反馈修订）、SQL-of-Thought（错误分类引导修正）

**实现方案**：

1. **语法验证**：
   - 使用 `pg_query` 库（PostgreSQL 解析器的 Python 绑定）或直接 `EXPLAIN` 验证
   - 检查引用的表/列是否存在于 schema 中

2. **执行反馈自修正**：
   - 若 SQL 执行报错，将错误信息反馈给 LLM，请求修正
   - 最多重试 `max_retries` 次（默认 2）
   - 参考 SQL-of-Thought 的错误分类法：语法错误、列不存在、类型不匹配、JOIN 条件缺失等

3. **逻辑验证（进阶）**：
   - 对生成的 SQL 做 `EXPLAIN` 分析，检查是否全表扫描等性能问题
   - 若查询涉及自定义算子（如 `ai_filter`），验证参数类型是否正确

**新增参数**：
```python
def ai_query(
    model_name: str,
    user_prompt: str,
    schema_info: Optional[str] = None,
    num_candidates: int = 1,
    use_cot: bool = False,
    auto_correct: bool = True,
    max_retries: int = 2,
) -> str:
```

### 阶段5: 候选选择（Self-Consistency）

**目标**：从多个候选 SQL 中选出最可靠的结果。

**参考方案**：CHASE-SQL、MCS-SQL

**实现方案**：

1. **执行结果投票**：
   - 当 `num_candidates > 1` 时，执行所有候选 SQL
   - 比较执行结果，选择结果一致最多的 SQL（self-consistency）
   - 若所有候选结果不同，选择语法最简单且执行成功的

2. **LLM 裁决（可选）**：
   - 当投票无法决出胜者时，用 LLM 从候选中选出最合理的
   - 输入：原始问题 + 各候选 SQL + 各执行结果摘要
   - 输出：最优 SQL 的编号

### 阶段6: 安全检查与输出

**目标**：防止 SQL 注入、危险操作，确保数据安全。

**实现方案**：

1. **危险操作过滤**：
   - 禁止 `DROP`、`DELETE`、`UPDATE`、`INSERT`、`TRUNCATE`、`ALTER` 等 DDL/DML 语句
   - 只允许 `SELECT` 查询（可配置）

2. **SQL 注入防护**：
   - 检测常见注入模式（如 `; DROP TABLE`、`UNION SELECT` 等）
   - 限制查询复杂度（最大嵌套深度、最大 JOIN 数量）

3. **查询超时保护**：
   - 为生成的 SQL 自动添加 `LIMIT`（若未指定）
   - 设置查询执行超时（`statement_timeout`）

**新增参数**：
```python
def ai_query(
    ...
    read_only: bool = True,
    max_limit: int = 1000,
    timeout_ms: int = 30000,
) -> str:
```

## 四、实现优先级与路线图

### Phase 1（高优先级，立即可做）

| 任务 | 改进点 | 预期效果 |
|------|--------|---------|
| 增强 `get_schema_info()` | 加入外键、列注释、示例值 | JOIN 准确率显著提升 |
| Schema 代码表示法 | 改用 `CREATE TABLE` DDL 格式 | LLM 理解 schema 更准确 |
| 算子注册表 | 在 prompt 中注入自定义算子说明 | 生成的 SQL 可调用 `ai_filter` 等 |
| SQL 安全检查 | 禁止 DDL/DML、自动加 LIMIT | 防止数据安全事故 |

### Phase 2（中优先级，1-2周）

| 任务 | 改进点 | 预期效果 |
|------|--------|---------|
| Few-shot 示例库 | `ai_query_examples` 表 + 动态示例选择 | 业务术语理解提升 |
| 领域知识注入 | `ai_query_knowledge` 表 | 模糊术语准确映射 |
| 执行反馈自修正 | 错误 SQL → 反馈 LLM → 修正 | 可执行 SQL 比例大幅提升 |
| Chain-of-Thought 模式 | 先推理再生成 | 复杂查询准确率提升 |

### Phase 3（进阶，2-4周）

| 任务 | 改进点 | 预期效果 |
|------|--------|---------|
| Schema Linking | `get_relevant_schema()` 智能筛选 | 大规模 schema 场景准确率提升 |
| 多候选生成 + Self-Consistency | `num_candidates` 参数 | 整体准确率提升 10-15% |
| 历史查询学习 | 参考 TailorSQL，从 `pg_stat_statements` 提取常见 JOIN 路径 | 多表查询准确率提升 |
| SQL 语法约束解码 | 限制 LLM 只生成合法 SQL 结构 | 语法错误率接近 0 |

## 五、关键代码改动概览

### 1. `ai_query.py` 重构

```python
# 核心流程伪代码
def ai_query(model_name, user_prompt, schema_info=None, ...):
    # Phase 1: Schema Linking
    if schema_info is None:
        schema_info = get_relevant_schema(model_name, user_prompt)

    # Phase 2: Build Enhanced Prompt
    prompt = build_prompt(
        user_prompt,
        schema_info,
        operator_registry=get_operator_registry(),
        examples=retrieve_similar_examples(user_prompt),
        knowledge=retrieve_knowledge(user_prompt)
    )

    # Phase 3: Multi-candidate Generation
    candidates = []
    for i in range(num_candidates):
        sql = generate_sql(model_name, prompt, variant=i)
        candidates.append(sql)

    # Phase 4: Validation & Self-Correction
    validated = []
    for sql in candidates:
        if auto_correct:
            sql = self_correct(model_name, sql, schema_info, max_retries)
        if validate_sql(sql, schema_info):
            validated.append(sql)

    # Phase 5: Candidate Selection
    if len(validated) > 1:
        best_sql = select_best(validated, user_prompt, model_name)
    elif len(validated) == 1:
        best_sql = validated[0]
    else:
        return "无法生成有效的 SQL 查询"

    # Phase 6: Security Check
    if not security_check(best_sql, read_only=True):
        return "生成的 SQL 包含不允许的操作"

    return best_sql
```

### 2. 新增模块

```
pg_semantic_operators/operators/
├── ai_query.py              # 重构：六阶段流水线
├── ai_query/
│   ├── __init__.py          # 导出
│   ├── schema_linking.py    # Schema Linking 模块
│   ├── prompt_builder.py    # Prompt 构建模块（含算子注册、few-shot）
│   ├── validator.py         # SQL 验证与自修正模块
│   ├── selector.py          # 候选选择模块
│   └── security.py          # 安全检查模块
```

### 3. SQL 扩展更新

新增函数和表定义到 `pg_semantic_operators--1.0.sql`（或新版本迁移脚本 `--2.0.sql`）。

## 六、预期收益

| 指标 | 当前水平 | Phase 1 后 | Phase 2 后 | Phase 3 后 |
|------|---------|-----------|-----------|-----------|
| 单表查询准确率 | ~70-80% | ~85-90% | ~90-95% | ~95%+ |
| 多表 JOIN 准确率 | ~40-50% | ~60-70% | ~70-80% | ~80-85% |
| SQL 语法正确率 | ~80% | ~95% | ~98% | ~99%+ |
| 可调用自定义算子 | ❌ | ✅ | ✅ | ✅ |
| 自动错误修正 | ❌ | ❌ | ✅ | ✅ |
| 安全防护 | ❌ | ✅ | ✅ | ✅ |
