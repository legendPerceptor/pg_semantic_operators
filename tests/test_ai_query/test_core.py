"""Tests for the core ai_query pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from pg_semantic_operators.operators.ai_query.core import ai_query


class TestAiQueryPipeline:
    def _mock_model_response(self, sql):
        """Helper: returns a mock call_model function that produces a SQL code block."""
        def mock_fn(name, prompt):
            return f"```sql\n{sql}\n```"
        return mock_fn

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_basic_sql_generation(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM users;\n```"
        result = ai_query("minimax", "查找所有用户")
        assert "SELECT" in result
        assert "users" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_non_sql_response_returned_as_is(self, mock_call):
        mock_call.return_value = "抱歉，我需要更多信息来生成SQL。"
        result = ai_query("minimax", "hello")
        assert "抱歉" in result
        assert "SQL" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_with_schema_info(self, mock_call):
        mock_call.return_value = "```sql\nSELECT id, name FROM orders WHERE amount > 100;\n```"
        schema = "CREATE TABLE orders (id INT, name TEXT, amount FLOAT);"
        result = ai_query("minimax", "查找大额订单", schema_info=schema)
        assert "SELECT" in result
        assert "orders" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_dangerous_sql_blocked(self, mock_call):
        mock_call.return_value = "```sql\nDROP TABLE users;\n```"
        result = ai_query("minimax", "删除用户表")
        assert "安全检查" in result or "验证失败" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_auto_limit_added(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM users;\n```"
        result = ai_query("minimax", "查找所有用户", max_limit=100)
        assert "LIMIT" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_max_limit_zero_no_limit(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM users;\n```"
        result = ai_query("minimax", "查找所有用户", max_limit=0)
        assert "LIMIT" not in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_auto_correct_fixes_sql(self, mock_call):
        """First call returns bad SQL, correction call returns good SQL."""
        mock_call.side_effect = [
            "```sql\nSELEC * FROM users;\n```",  # initial bad SQL
            "```sql\nSELECT * FROM users;\n```",  # corrected SQL
        ]
        result = ai_query("minimax", "查找用户", auto_correct=True)
        assert "SELECT" in result
        assert "安全检查" not in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_auto_correct_disabled(self, mock_call):
        mock_call.return_value = "```sql\nSELEC * FROM users;\n```"
        result = ai_query("minimax", "查找用户", auto_correct=False)
        assert "验证失败" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_with_examples(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM orders LIMIT 10;\n```"
        examples = [{"question": "找订单", "sql_query": "SELECT * FROM orders LIMIT 10;"}]
        result = ai_query("minimax", "找订单", examples=examples)
        assert "SELECT" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_with_knowledge(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM orders WHERE amount > 10000;\n```"
        knowledge = [{"term": "高价值订单", "definition": "金额>10000"}]
        result = ai_query("minimax", "查找高价值订单", knowledge=knowledge)
        assert "SELECT" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_read_only_blocks_non_select(self, mock_call):
        mock_call.return_value = "```sql\nINSERT INTO users VALUES (1, 'a');\n```"
        result = ai_query("minimax", "插入数据", read_only=True)
        assert "安全检查" in result or "验证失败" in result

    @patch("pg_semantic_operators.operators.ai_query.core.call_model")
    def test_preserves_existing_limit(self, mock_call):
        mock_call.return_value = "```sql\nSELECT * FROM users LIMIT 5;\n```"
        result = ai_query("minimax", "查5个用户", max_limit=100)
        # Should keep the original LIMIT 5, not add LIMIT 100
        assert "LIMIT 5" in result
