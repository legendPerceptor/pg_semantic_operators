"""Tests for prompt_builder module."""

import pytest
from pg_semantic_operators.operators.ai_query.prompt_builder import (
    build_prompt,
    extract_sql_from_response,
    _build_operator_section,
    _build_knowledge_section,
    _build_example_section,
    AI_QUERY_SYSTEM_PROMPT,
    OPERATOR_REGISTRY,
)


class TestBuildOperatorSection:
    def test_includes_all_operators(self):
        section = _build_operator_section()
        for name in OPERATOR_REGISTRY:
            assert name in section

    def test_contains_signature_and_description(self):
        section = _build_operator_section()
        assert "签名:" in section
        assert "说明:" in section
        assert "示例:" in section

    def test_contains_sql_code_blocks(self):
        section = _build_operator_section()
        assert "```sql" in section


class TestBuildKnowledgeSection:
    def test_empty_knowledge(self):
        assert _build_knowledge_section(None) == ""
        assert _build_knowledge_section([]) == ""

    def test_with_entries(self):
        knowledge = [
            {"term": "高价值订单", "definition": "金额超过10000元的订单"},
            {"term": "活跃用户", "definition": "最近30天内有登录的用户"},
        ]
        section = _build_knowledge_section(knowledge)
        assert "高价值订单" in section
        assert "金额超过10000元的订单" in section
        assert "活跃用户" in section

    def test_skips_incomplete_entries(self):
        knowledge = [
            {"term": "valid", "definition": "ok"},
            {"term": "", "definition": "no term"},
            {"term": "no def", "definition": ""},
        ]
        section = _build_knowledge_section(knowledge)
        assert "valid" in section
        assert "no term" not in section
        assert "no def" not in section


class TestBuildExampleSection:
    def test_empty_examples(self):
        assert _build_example_section(None) == ""
        assert _build_example_section([]) == ""

    def test_with_examples(self):
        examples = [
            {"question": "查找所有订单", "sql_query": "SELECT * FROM orders LIMIT 10;"},
            {"question": "统计用户数", "sql_query": "SELECT COUNT(*) FROM users;"},
        ]
        section = _build_example_section(examples)
        assert "示例 1:" in section
        assert "示例 2:" in section
        assert "查找所有订单" in section
        assert "SELECT * FROM orders" in section

    def test_skips_incomplete_examples(self):
        examples = [
            {"question": "valid q", "sql_query": "SELECT 1"},
            {"question": "", "sql_query": "SELECT 2"},
            {"question": "no sql", "sql_query": ""},
        ]
        section = _build_example_section(examples)
        assert "valid q" in section
        assert "no sql" not in section


class TestBuildPrompt:
    def test_basic_prompt(self):
        prompt = build_prompt(user_prompt="查找所有用户")
        assert "查找所有用户" in prompt
        assert "用户请求" in prompt

    def test_with_schema_info(self):
        schema = "CREATE TABLE users (id INT, name TEXT);"
        prompt = build_prompt(user_prompt="查找用户", schema_info=schema)
        assert schema in prompt
        assert "DDL格式" in prompt

    def test_without_operators(self):
        prompt = build_prompt(user_prompt="test", include_operators=False)
        # 算子注册表段不应包含详细签名和说明
        assert "签名:" not in prompt
        assert "说明:" not in prompt

    def test_with_operators(self):
        prompt = build_prompt(user_prompt="test", include_operators=True)
        assert "ai_filter" in prompt

    def test_full_prompt_with_all_sections(self):
        prompt = build_prompt(
            user_prompt="查找高价值订单",
            schema_info="CREATE TABLE orders (id INT, amount FLOAT);",
            include_operators=True,
            examples=[{"question": "找大订单", "sql_query": "SELECT * FROM orders WHERE amount > 1000"}],
            knowledge=[{"term": "高价值", "definition": "金额>10000"}],
        )
        assert "查找高价值订单" in prompt
        assert "CREATE TABLE orders" in prompt
        assert "ai_filter" in prompt
        assert "找大订单" in prompt
        assert "高价值" in prompt

    def test_system_prompt_template_has_placeholders(self):
        assert "{schema_section}" in AI_QUERY_SYSTEM_PROMPT
        assert "{operator_section}" in AI_QUERY_SYSTEM_PROMPT
        assert "{knowledge_section}" in AI_QUERY_SYSTEM_PROMPT
        assert "{example_section}" in AI_QUERY_SYSTEM_PROMPT


class TestExtractSqlFromResponse:
    def test_extract_from_sql_code_block(self):
        response = '这是一个查询：\n```sql\nSELECT * FROM users;\n```\n希望对你有帮助。'
        assert extract_sql_from_response(response) == "SELECT * FROM users;"

    def test_extract_plain_sql(self):
        response = "SELECT * FROM users;"
        assert extract_sql_from_response(response) == "SELECT * FROM users;"

    def test_extract_with_surrounding_backticks(self):
        response = "```sql\nSELECT 1;\n```"
        assert extract_sql_from_response(response) == "SELECT 1;"

    def test_multiline_sql(self):
        response = "```sql\nSELECT u.name,\n       COUNT(*)\nFROM users u\nJOIN orders o ON u.id = o.user_id\nGROUP BY u.name;\n```"
        result = extract_sql_from_response(response)
        assert "SELECT u.name," in result
        assert "GROUP BY u.name;" in result

    def test_empty_response(self):
        assert extract_sql_from_response("") == ""
        assert extract_sql_from_response("   ") == ""

    def test_no_sql_block(self):
        response = "抱歉，我需要更多信息来生成SQL。"
        assert "抱歉" in extract_sql_from_response(response)

    def test_code_block_without_language(self):
        response = "```\nSELECT * FROM orders;\n```"
        result = extract_sql_from_response(response)
        assert "SELECT * FROM orders;" in result
