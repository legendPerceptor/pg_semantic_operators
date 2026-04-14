"""Tests for security module."""

import pytest
from pg_semantic_operators.operators.ai_query.security import (
    security_check,
    ensure_limit,
    sanitize_sql,
)


class TestSecurityCheck:
    # --- Safe queries ---
    def test_safe_select(self):
        is_safe, error = security_check("SELECT * FROM users;")
        assert is_safe is True
        assert error is None

    def test_safe_select_with_join(self):
        sql = "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id;"
        is_safe, error = security_check(sql)
        assert is_safe is True

    def test_safe_with_subquery(self):
        sql = "SELECT * FROM (SELECT id FROM users) AS sub;"
        is_safe, error = security_check(sql)
        assert is_safe is True

    # --- Empty / invalid input ---
    def test_empty_sql(self):
        is_safe, error = security_check("")
        assert is_safe is False
        assert "空" in error

    def test_whitespace_only(self):
        is_safe, error = security_check("   ")
        assert is_safe is False

    # --- Dangerous statements ---
    def test_drop_table(self):
        is_safe, error = security_check("SELECT 1; DROP TABLE users;")
        assert is_safe is False

    def test_delete(self):
        is_safe, error = security_check("SELECT 1; DELETE FROM users;")
        assert is_safe is False

    def test_update(self):
        is_safe, error = security_check("SELECT 1; UPDATE users SET x=1;")
        assert is_safe is False

    def test_insert(self):
        is_safe, error = security_check("SELECT 1; INSERT INTO users VALUES (1);")
        assert is_safe is False

    def test_truncate(self):
        is_safe, error = security_check("SELECT 1; TRUNCATE TABLE users;")
        assert is_safe is False

    def test_alter(self):
        is_safe, error = security_check("SELECT 1; ALTER TABLE users ADD COLUMN x INT;")
        assert is_safe is False

    def test_grant(self):
        is_safe, error = security_check("SELECT 1; GRANT ALL ON users TO public;")
        assert is_safe is False

    def test_revoke(self):
        is_safe, error = security_check("SELECT 1; REVOKE ALL ON users FROM public;")
        assert is_safe is False

    def test_vacuum(self):
        is_safe, error = security_check("SELECT 1; VACUUM users;")
        assert is_safe is False

    # --- System catalog access ---
    def test_pg_catalog(self):
        is_safe, error = security_check("SELECT * FROM pg_catalog.pg_class;")
        assert is_safe is False

    def test_information_schema(self):
        is_safe, error = security_check("SELECT * FROM information_schema.tables;")
        assert is_safe is False

    def test_pg_system_table(self):
        is_safe, error = security_check("SELECT * FROM pg_stat.activity;")
        assert is_safe is False

    # --- Injection patterns ---
    def test_union_injection(self):
        is_safe, error = security_check("SELECT * FROM users UNION ALL SELECT * FROM admins;")
        assert is_safe is False

    def test_or_1_eq_1(self):
        is_safe, error = security_check("SELECT * FROM users WHERE id = 1 OR 1=1;")
        assert is_safe is False

    def test_string_injection(self):
        is_safe, error = security_check("SELECT * FROM users WHERE name = '' OR '1'='1';")
        assert is_safe is False

    def test_copy_statement(self):
        is_safe, error = security_check("SELECT 1; COPY users TO '/tmp/out';")
        assert is_safe is False

    def test_into_outfile(self):
        is_safe, error = security_check("SELECT * INTO OUTFILE '/tmp/out' FROM users;")
        assert is_safe is False

    def test_load_file(self):
        is_safe, error = security_check("SELECT LOAD_FILE('/etc/passwd');")
        assert is_safe is False

    def test_pg_read_file(self):
        is_safe, error = security_check("SELECT pg_read_file('/etc/passwd');")
        assert is_safe is False

    def test_dblink(self):
        is_safe, error = security_check("SELECT * FROM dblink('host=evil', 'SELECT 1');")
        assert is_safe is False

    # --- Read-only enforcement ---
    def test_read_only_blocks_non_select(self):
        is_safe, error = security_check("INSERT INTO users VALUES (1, 'a');", read_only=True)
        assert is_safe is False
        assert "只读" in error

    def test_read_only_allows_select(self):
        is_safe, error = security_check("SELECT * FROM users;", read_only=True)
        assert is_safe is True

    def test_read_only_allows_with(self):
        is_safe, error = security_check(
            "WITH cte AS (SELECT 1) SELECT * FROM cte;", read_only=True
        )
        assert is_safe is True

    def test_read_only_allows_explain(self):
        is_safe, error = security_check("EXPLAIN SELECT * FROM users;", read_only=True)
        assert is_safe is True

    def test_non_read_only_allows_more(self):
        is_safe, error = security_check(
            "SELECT * FROM users;", read_only=False
        )
        assert is_safe is True

    # --- Complexity limits ---
    def test_too_many_joins(self):
        joins = " ".join([f"JOIN t{i} ON t{i}.id = t0.id" for i in range(1, 12)])
        sql = f"SELECT * FROM t0 {joins};"
        is_safe, error = security_check(sql)
        assert is_safe is False
        assert "JOIN" in error

    def test_ok_join_count(self):
        joins = " ".join([f"JOIN t{i} ON t{i}.id = t0.id" for i in range(1, 5)])
        sql = f"SELECT * FROM t0 {joins};"
        is_safe, error = security_check(sql)
        assert is_safe is True

    def test_too_deep_nesting(self):
        sql = "SELECT * FROM " + "((((((" + "SELECT 1" + "))))));"
        # 6 levels of nesting > _MAX_NESTING_DEPTH=5
        is_safe, error = security_check(sql)
        assert is_safe is False
        assert "嵌套" in error

    def test_acceptable_nesting(self):
        sql = "SELECT * FROM ((SELECT * FROM (SELECT 1) AS sub)) AS outer;"
        is_safe, error = security_check(sql)
        assert is_safe is True


class TestEnsureLimit:
    def test_adds_limit_when_missing(self):
        result = ensure_limit("SELECT * FROM users;")
        assert "LIMIT 1000" in result

    def test_preserves_existing_limit(self):
        result = ensure_limit("SELECT * FROM users LIMIT 50;")
        assert "LIMIT 50" in result
        assert "LIMIT 1000" not in result

    def test_adds_limit_after_order_by(self):
        result = ensure_limit("SELECT * FROM users ORDER BY name;")
        assert "LIMIT 1000" in result
        assert "ORDER BY name LIMIT 1000" in result

    def test_custom_default_limit(self):
        result = ensure_limit("SELECT * FROM users;", default_limit=100)
        assert "LIMIT 100" in result

    def test_disabled_with_zero(self):
        result = ensure_limit("SELECT * FROM users;", default_limit=0)
        assert "LIMIT" not in result

    def test_adds_semicolon(self):
        result = ensure_limit("SELECT * FROM users")
        assert result.endswith(";")

    def test_preserves_existing_semicolon(self):
        result = ensure_limit("SELECT * FROM users;")
        assert result.count(";") == 1


class TestSanitizeSql:
    def test_strips_whitespace(self):
        assert sanitize_sql("  SELECT 1;  ") == "SELECT 1"

    def test_removes_trailing_semicolon(self):
        assert sanitize_sql("SELECT 1;") == "SELECT 1"

    def test_normalizes_internal_whitespace(self):
        result = sanitize_sql("SELECT  *   FROM   users;")
        assert result == "SELECT * FROM users"

    def test_already_clean(self):
        assert sanitize_sql("SELECT * FROM users") == "SELECT * FROM users"

    def test_empty_string(self):
        assert sanitize_sql("") == ""

    def test_only_whitespace(self):
        assert sanitize_sql("   ") == ""

    def test_multiple_trailing_semicolons(self):
        result = sanitize_sql("SELECT 1;;")
        # sanitize_sql only strips one trailing ; after whitespace normalization
        # "SELECT 1;;" -> strip -> "SELECT 1;;" -> normalize -> "SELECT 1;;" -> strip trailing ; -> "SELECT 1;"
        assert "SELECT 1" in result
