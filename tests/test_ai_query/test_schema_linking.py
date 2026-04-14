"""Tests for schema_linking module."""

import json
import pytest
from unittest.mock import MagicMock
from pg_semantic_operators.operators.ai_query.schema_linking import (
    get_schema_info_enhanced,
    get_relevant_schema,
    get_schema_info_basic,
)


def _make_plpy_mock(rows, pk_rows=None, fk_rows=None, example_values=None):
    """Create a mock plpy object with configurable query results.

    Args:
        rows: Main schema query results (list of dicts)
        pk_rows: Primary key query results
        fk_rows: Foreign key query results
        example_values: Dict mapping "table.column" -> list of value dicts
    """
    mock = MagicMock()

    def execute_side_effect(sql):
        # Match based on SQL content
        if "PRIMARY KEY" in sql:
            return pk_rows or []
        if "FOREIGN KEY" in sql:
            return fk_rows or []
        if "DISTINCT" in sql and "LIMIT 3" in sql:
            # Example values query
            if example_values:
                for key, vals in example_values.items():
                    if key in sql:
                        return vals
            return []
        return rows

    mock.execute.side_effect = execute_side_effect
    return mock


class TestGetSchemaInfoEnhanced:
    def test_basic_table(self):
        rows = [
            {
                "table_name": "users",
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": "nextval('users_id_seq'::regclass)",
                "table_comment": "用户表",
                "column_comment": "用户ID",
            },
            {
                "table_name": "users",
                "column_name": "name",
                "data_type": "text",
                "is_nullable": "YES",
                "column_default": None,
                "table_comment": "用户表",
                "column_comment": "用户名",
            },
        ]
        plpy = _make_plpy_mock(rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=False)

        assert "CREATE TABLE users" in result
        assert "id integer" in result
        assert "NOT NULL" in result
        assert "name text" in result
        assert "PRIMARY KEY" not in result  # no pk_rows provided

    def test_with_primary_key(self):
        rows = [
            {
                "table_name": "users",
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "table_comment": "",
                "column_comment": "",
            },
        ]
        pk_rows = [{"table_name": "users", "column_name": "id"}]
        plpy = _make_plpy_mock(rows, pk_rows=pk_rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=False)

        assert "PRIMARY KEY (id)" in result

    def test_with_foreign_key(self):
        rows = [
            {
                "table_name": "orders",
                "column_name": "user_id",
                "data_type": "integer",
                "is_nullable": "YES",
                "column_default": None,
                "table_comment": "",
                "column_comment": "",
            },
        ]
        fk_rows = [
            {
                "constraint_name": "fk_orders_user",
                "from_table": "orders",
                "from_column": "user_id",
                "to_table": "users",
                "to_column": "id",
            }
        ]
        plpy = _make_plpy_mock(rows, fk_rows=fk_rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=True)

        assert "FOREIGN KEY (user_id) REFERENCES users(id)" in result

    def test_with_comments(self):
        rows = [
            {
                "table_name": "products",
                "column_name": "price",
                "data_type": "numeric",
                "is_nullable": "YES",
                "column_default": None,
                "table_comment": "产品表",
                "column_comment": "价格（元）",
            },
        ]
        plpy = _make_plpy_mock(rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=False)

        assert "产品表" in result
        assert "价格（元）" in result

    def test_multiple_tables(self):
        rows = [
            {
                "table_name": "users",
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "table_comment": "",
                "column_comment": "",
            },
            {
                "table_name": "orders",
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": None,
                "table_comment": "",
                "column_comment": "",
            },
        ]
        plpy = _make_plpy_mock(rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=False)

        assert "CREATE TABLE users" in result
        assert "CREATE TABLE orders" in result

    def test_error_returns_error_string(self):
        mock_plpy = MagicMock()
        mock_plpy.execute.side_effect = Exception("connection lost")
        result = get_schema_info_enhanced(mock_plpy)
        assert "Error" in result

    def test_column_with_default(self):
        rows = [
            {
                "table_name": "settings",
                "column_name": "active",
                "data_type": "boolean",
                "is_nullable": "NO",
                "column_default": "true",
                "table_comment": "",
                "column_comment": "",
            },
        ]
        plpy = _make_plpy_mock(rows)
        result = get_schema_info_enhanced(plpy, include_examples=False, include_foreign_keys=False)

        assert "DEFAULT true" in result


class TestGetRelevantSchema:
    def test_few_tables_returns_all(self):
        """If <= 3 tables, returns full schema without calling model."""
        full_schema = (
            "CREATE TABLE users (\n  id integer NOT NULL\n);\n\n"
            "CREATE TABLE orders (\n  id integer NOT NULL\n);\n"
        )
        plpy = MagicMock()
        result = get_relevant_schema(plpy, "model", "查找用户", full_schema=full_schema)
        assert "CREATE TABLE users" in result
        assert "CREATE TABLE orders" in result

    def test_model_selects_relevant_tables(self):
        """Model returns specific tables, only those are kept."""
        full_schema = (
            "CREATE TABLE users (\n  id integer NOT NULL\n);\n\n"
            "CREATE TABLE orders (\n  id integer NOT NULL\n);\n\n"
            "CREATE TABLE products (\n  id integer NOT NULL\n);\n\n"
            "CREATE TABLE logs (\n  id integer NOT NULL\n);\n"
        )

        def mock_call_model(name, prompt):
            return '["users", "orders"]'

        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "查找用户订单",
            full_schema=full_schema,
            call_model_fn=mock_call_model,
        )
        assert "CREATE TABLE users" in result
        assert "CREATE TABLE orders" in result
        assert "CREATE TABLE products" not in result
        assert "CREATE TABLE logs" not in result

    def test_model_returns_json_in_code_block(self):
        full_schema = (
            "CREATE TABLE users (\n  id integer\n);\n\n"
            "CREATE TABLE orders (\n  id integer\n);\n\n"
            "CREATE TABLE products (\n  id integer\n);\n\n"
            "CREATE TABLE logs (\n  id integer\n);\n"
        )

        def mock_call_model(name, prompt):
            return '```json\n["users"]\n```'

        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "查找用户",
            full_schema=full_schema,
            call_model_fn=mock_call_model,
        )
        assert "CREATE TABLE users" in result

    def test_model_failure_returns_full_schema(self):
        full_schema = (
            "CREATE TABLE users (\n  id integer\n);\n\n"
            "CREATE TABLE orders (\n  id integer\n);\n\n"
            "CREATE TABLE products (\n  id integer\n);\n\n"
            "CREATE TABLE logs (\n  id integer\n);\n"
        )

        def mock_call_model(name, prompt):
            raise RuntimeError("API down")

        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "查找用户",
            full_schema=full_schema,
            call_model_fn=mock_call_model,
        )
        # Falls back to full schema
        assert result == full_schema

    def test_no_call_model_fn_returns_full(self):
        full_schema = (
            "CREATE TABLE a (\n  id integer\n);\n\n"
            "CREATE TABLE b (\n  id integer\n);\n\n"
            "CREATE TABLE c (\n  id integer\n);\n\n"
            "CREATE TABLE d (\n  id integer\n);\n"
        )
        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "test",
            full_schema=full_schema,
            call_model_fn=None,
        )
        assert result == full_schema

    def test_model_returns_empty_list_falls_back(self):
        full_schema = (
            "CREATE TABLE a (\n  id integer\n);\n\n"
            "CREATE TABLE b (\n  id integer\n);\n\n"
            "CREATE TABLE c (\n  id integer\n);\n\n"
            "CREATE TABLE d (\n  id integer\n);\n"
        )

        def mock_call_model(name, prompt):
            return "[]"

        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "test",
            full_schema=full_schema,
            call_model_fn=mock_call_model,
        )
        assert result == full_schema

    def test_model_returns_invalid_json_falls_back(self):
        full_schema = (
            "CREATE TABLE a (\n  id integer\n);\n\n"
            "CREATE TABLE b (\n  id integer\n);\n\n"
            "CREATE TABLE c (\n  id integer\n);\n\n"
            "CREATE TABLE d (\n  id integer\n);\n"
        )

        def mock_call_model(name, prompt):
            return "not json at all"

        plpy = MagicMock()
        result = get_relevant_schema(
            plpy, "model", "test",
            full_schema=full_schema,
            call_model_fn=mock_call_model,
        )
        assert result == full_schema


class TestGetSchemaInfoBasic:
    def test_basic_output(self):
        rows = [
            {"table_name": "users", "column_name": "id", "data_type": "integer", "is_nullable": "NO"},
            {"table_name": "users", "column_name": "name", "data_type": "text", "is_nullable": "YES"},
        ]
        mock_plpy = MagicMock()
        mock_plpy.execute.return_value = rows

        result = get_schema_info_basic(mock_plpy)
        assert "表: users" in result
        assert "id (integer) NOT NULL" in result
        assert "name (text) NULL" in result

    def test_error_handling(self):
        mock_plpy = MagicMock()
        mock_plpy.execute.side_effect = Exception("db error")
        result = get_schema_info_basic(mock_plpy)
        assert "无法获取" in result or "error" in result.lower()
