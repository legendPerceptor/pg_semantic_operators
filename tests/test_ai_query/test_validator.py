"""Tests for validator module."""

import pytest
from pg_semantic_operators.operators.ai_query.validator import (
    validate_sql_syntax,
    classify_error,
    build_correction_prompt,
    self_correct,
)


class TestValidateSqlSyntax:
    def test_valid_select(self):
        is_valid, error = validate_sql_syntax("SELECT * FROM users;")
        assert is_valid is True
        assert error is None

    def test_valid_with_cte(self):
        is_valid, error = validate_sql_syntax(
            "WITH active AS (SELECT * FROM users WHERE active = true) SELECT * FROM active;"
        )
        assert is_valid is True
        assert error is None

    def test_valid_starting_with_paren(self):
        is_valid, error = validate_sql_syntax("(SELECT * FROM users) UNION (SELECT * FROM admins);")
        assert is_valid is True
        assert error is None

    def test_empty_sql(self):
        is_valid, error = validate_sql_syntax("")
        assert is_valid is False
        assert "空" in error

    def test_whitespace_only(self):
        is_valid, error = validate_sql_syntax("   \n\t  ")
        assert is_valid is False

    def test_dangerous_drop(self):
        is_valid, error = validate_sql_syntax("DROP TABLE users;")
        assert is_valid is False
        assert "DROP" in error

    def test_dangerous_delete(self):
        is_valid, error = validate_sql_syntax("DELETE FROM users;")
        assert is_valid is False
        assert "DELETE" in error

    def test_dangerous_update(self):
        is_valid, error = validate_sql_syntax("UPDATE users SET name = 'hacked';")
        assert is_valid is False
        assert "UPDATE" in error

    def test_dangerous_insert(self):
        is_valid, error = validate_sql_syntax("INSERT INTO users VALUES (1, 'hack');")
        assert is_valid is False
        assert "INSERT" in error

    def test_dangerous_truncate(self):
        is_valid, error = validate_sql_syntax("TRUNCATE TABLE users;")
        assert is_valid is False
        assert "TRUNCATE" in error

    def test_dangerous_alter(self):
        is_valid, error = validate_sql_syntax("ALTER TABLE users ADD COLUMN x INT;")
        assert is_valid is False
        assert "ALTER" in error

    def test_dangerous_create(self):
        is_valid, error = validate_sql_syntax("CREATE TABLE evil (id INT);")
        assert is_valid is False
        assert "CREATE" in error

    def test_non_select_start(self):
        is_valid, error = validate_sql_syntax("DESCRIBE users;")
        assert is_valid is False
        assert "SELECT" in error or "WITH" in error

    def test_unbalanced_parentheses_extra_close(self):
        is_valid, error = validate_sql_syntax("SELECT * FROM (users));")
        assert is_valid is False
        assert "括号" in error

    def test_unbalanced_parentheses_missing_close(self):
        is_valid, error = validate_sql_syntax("SELECT * FROM (SELECT * FROM users;")
        assert is_valid is False
        assert "括号" in error

    def test_unbalanced_single_quotes(self):
        is_valid, error = validate_sql_syntax("SELECT * FROM users WHERE name = 'test;")
        assert is_valid is False
        assert "引号" in error

    def test_complex_valid_sql(self):
        sql = (
            "SELECT u.name, COUNT(o.id) "
            "FROM users u "
            "JOIN orders o ON u.id = o.user_id "
            "WHERE u.active = true AND o.amount > 100 "
            "GROUP BY u.name "
            "HAVING COUNT(o.id) > 5 "
            "ORDER BY COUNT(o.id) DESC;"
        )
        is_valid, error = validate_sql_syntax(sql)
        assert is_valid is True

    def test_explain_allowed(self):
        is_valid, error = validate_sql_syntax("EXPLAIN SELECT * FROM users;")
        assert is_valid is True

    def test_dangerous_after_semicolon(self):
        is_valid, error = validate_sql_syntax("SELECT 1; DROP TABLE users;")
        assert is_valid is False
        assert "DROP" in error


class TestClassifyError:
    def test_syntax_error(self):
        error_type, hint = classify_error("syntax error at or near \"SELEC\"")
        assert error_type == "syntax_error"

    def test_column_not_found(self):
        error_type, hint = classify_error('column "xyz" does not exist')
        assert error_type == "column_not_found"

    def test_table_not_found(self):
        error_type, hint = classify_error('relation "foobar" does not exist')
        assert error_type == "table_not_found"

    def test_type_mismatch(self):
        error_type, hint = classify_error("operator does not exist: text = integer")
        assert error_type == "type_mismatch"

    def test_join_missing(self):
        error_type, hint = classify_error("invalid reference to FROM-clause entry")
        assert error_type == "join_missing"

    def test_function_not_found(self):
        error_type, hint = classify_error("function ai_filter() does not exist")
        assert error_type == "function_not_found"

    def test_unknown_error(self):
        error_type, hint = classify_error("some random error")
        assert error_type == "unknown"

    def test_case_insensitive(self):
        error_type, hint = classify_error("SYNTAX ERROR near SELECT")
        assert error_type == "syntax_error"


class TestBuildCorrectionPrompt:
    def test_basic_correction_prompt(self):
        prompt = build_correction_prompt(
            original_question="查找所有用户",
            original_sql="SELEC * FROM users;",
            error_message="syntax error at or near \"SELEC\"",
        )
        assert "查找所有用户" in prompt
        assert "SELEC * FROM users" in prompt
        assert "syntax error" in prompt
        assert "修正后的 SQL" in prompt

    def test_with_schema(self):
        prompt = build_correction_prompt(
            original_question="test",
            original_sql="bad sql",
            error_message="error",
            schema_info="CREATE TABLE users (id INT);",
        )
        assert "CREATE TABLE users" in prompt

    def test_includes_error_type_and_hint(self):
        prompt = build_correction_prompt(
            original_question="q",
            original_sql="s",
            error_message='column "foo" does not exist',
        )
        assert "column_not_found" in prompt
        assert "列名" in prompt


class TestSelfCorrect:
    def test_no_model_fn_returns_original(self):
        sql, corrected = self_correct(
            model_name="test",
            original_question="q",
            original_sql="BAD SQL",
            error_message="error",
            call_model_fn=None,
        )
        assert corrected is False
        assert sql == "BAD SQL"

    def test_successful_correction(self):
        def mock_model(name, prompt):
            return "```sql\nSELECT * FROM users;\n```"

        sql, corrected = self_correct(
            model_name="test",
            original_question="查找用户",
            original_sql="SELEC * FROM users;",
            error_message="syntax error",
            call_model_fn=mock_model,
            max_retries=2,
        )
        assert corrected is True
        assert "SELECT" in sql

    def test_correction_still_invalid(self):
        """Model returns invalid SQL, correction should fail."""
        call_count = [0]

        def mock_model(name, prompt):
            call_count[0] += 1
            return "```sql\nDROP TABLE users;\n```"

        sql, corrected = self_correct(
            model_name="test",
            original_question="q",
            original_sql="bad",
            error_message="error",
            call_model_fn=mock_model,
            max_retries=2,
        )
        assert corrected is False
        assert call_count[0] == 2  # retried max_retries times

    def test_model_raises_exception(self):
        def mock_model(name, prompt):
            raise RuntimeError("API error")

        sql, corrected = self_correct(
            model_name="test",
            original_question="q",
            original_sql="bad sql",
            error_message="error",
            call_model_fn=mock_model,
            max_retries=2,
        )
        assert corrected is False

    def test_model_returns_empty(self):
        def mock_model(name, prompt):
            return ""

        sql, corrected = self_correct(
            model_name="test",
            original_question="q",
            original_sql="bad",
            error_message="error",
            call_model_fn=mock_model,
            max_retries=1,
        )
        assert corrected is False
