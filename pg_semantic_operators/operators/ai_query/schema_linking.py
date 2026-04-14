"""Schema linking module for ai_query operator.

Provides enhanced schema information retrieval and relevant schema filtering
to improve NL2SQL accuracy.
"""

import json
import re
from typing import Optional


_SCHEMA_INFO_ENHANCED_SQL = """
SELECT
    t.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    obj_description(
        (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
        'pg_class'
    ) AS table_comment,
    col_description(
        (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
        c.ordinal_position
    ) AS column_comment
FROM information_schema.tables t
JOIN information_schema.columns c
    ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name, c.ordinal_position;
"""

_FK_INFO_SQL = """
SELECT
    tc.constraint_name,
    tc.table_name AS from_table,
    kcu.column_name AS from_column,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
    AND tc.table_schema = ccu.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;
"""

_PK_INFO_SQL = """
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;
"""

_EXAMPLE_VALUES_SQL_TEMPLATE = """
SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT 3;
"""


def get_schema_info_enhanced(
    plpy,
    include_examples: bool = True,
    include_foreign_keys: bool = True,
    max_example_tables: int = 20,
) -> str:
    """Get enhanced schema information as DDL-style CREATE TABLE statements.

    This replaces the old get_schema_info() with a richer format that includes:
    - CREATE TABLE DDL format (better for LLM code understanding)
    - Primary key constraints
    - Foreign key relationships
    - Column comments
    - Example values for each column

    Args:
        plpy: PostgreSQL PL/Python execution context
        include_examples: Whether to include example column values
        include_foreign_keys: Whether to include foreign key relationships
        max_example_tables: Max tables to fetch examples for (performance guard)

    Returns:
        DDL-style schema description string
    """
    try:
        result = plpy.execute(_SCHEMA_INFO_ENHANCED_SQL)
    except Exception as e:
        return f"-- Error fetching schema: {e}"

    tables = {}
    for row in result:
        table_name = row["table_name"]
        if table_name not in tables:
            tables[table_name] = {
                "columns": [],
                "table_comment": row.get("table_comment") or "",
            }
        tables[table_name]["columns"].append({
            "name": row["column_name"],
            "type": row["data_type"],
            "nullable": row["is_nullable"],
            "default": row.get("column_default"),
            "comment": row.get("column_comment") or "",
        })

    pk_info = {}
    try:
        pk_result = plpy.execute(_PK_INFO_SQL)
        for row in pk_result:
            table_name = row["table_name"]
            if table_name not in pk_info:
                pk_info[table_name] = []
            pk_info[table_name].append(row["column_name"])
    except Exception:
        pass

    fk_info = {}
    if include_foreign_keys:
        try:
            fk_result = plpy.execute(_FK_INFO_SQL)
            for row in fk_result:
                from_table = row["from_table"]
                if from_table not in fk_info:
                    fk_info[from_table] = []
                fk_info[from_table].append({
                    "column": row["from_column"],
                    "references_table": row["to_table"],
                    "references_column": row["to_column"],
                })
        except Exception:
            pass

    example_values = {}
    if include_examples:
        table_count = 0
        for table_name, table_data in tables.items():
            if table_count >= max_example_tables:
                break
            example_values[table_name] = {}
            for col in table_data["columns"]:
                try:
                    col_name = col["name"]
                    safe_col = col_name.replace('"', '""')
                    safe_table = table_name.replace('"', '""')
                    val_sql = _EXAMPLE_VALUES_SQL_TEMPLATE.format(
                        column=f'"{safe_col}"',
                        table=f'"{safe_table}"',
                    )
                    val_result = plpy.execute(val_sql)
                    values = [str(r[list(r.keys())[0]]) for r in val_result if r]
                    if values:
                        example_values[table_name][col_name] = values
                except Exception:
                    pass
            table_count += 1

    ddl_lines = []
    for table_name, table_data in tables.items():
        comment_suffix = ""
        if table_data["table_comment"]:
            comment_suffix = f"  -- {table_data['table_comment']}"

        ddl_lines.append(f"CREATE TABLE {table_name} ({comment_suffix}")

        col_lines = []
        for col in table_data["columns"]:
            parts = [f"  {col['name']} {col['type']}"]
            if col["nullable"] == "NO":
                parts.append("NOT NULL")
            if col.get("default"):
                parts.append(f"DEFAULT {col['default']}")
            col_comment = ""
            if col["comment"]:
                col_comment = f"  -- {col['comment']}"
            col_lines.append(" ".join(parts) + col_comment)

        if table_name in pk_info and pk_info[table_name]:
            pk_cols = ", ".join(pk_info[table_name])
            col_lines.append(f"  PRIMARY KEY ({pk_cols})")

        if include_foreign_keys and table_name in fk_info:
            for fk in fk_info[table_name]:
                col_lines.append(
                    f"  FOREIGN KEY ({fk['column']}) REFERENCES "
                    f"{fk['references_table']}({fk['references_column']})"
                )

        ddl_lines.append(",\n".join(col_lines))
        ddl_lines.append(");")

        if include_examples and table_name in example_values and example_values[table_name]:
            example_parts = []
            for col_name, values in example_values[table_name].items():
                vals_str = ", ".join(values[:3])
                example_parts.append(f"  {col_name}: [{vals_str}]")
            if example_parts:
                ddl_lines.append(f"-- Example values for {table_name}:")
                ddl_lines.append("\n".join(example_parts))

        ddl_lines.append("")

    return "\n".join(ddl_lines)


def get_relevant_schema(
    plpy,
    model_name: str,
    question: str,
    full_schema: Optional[str] = None,
    call_model_fn=None,
) -> str:
    """Filter schema to only include tables/columns relevant to the question.

    Uses LLM-based table selection to identify relevant tables, then returns
    only the DDL for those tables.

    Args:
        plpy: PostgreSQL PL/Python execution context
        model_name: LLM model name for table selection
        question: User's natural language question
        full_schema: Pre-fetched full schema (if None, will fetch)
        call_model_fn: Function to call the LLM model

    Returns:
        Filtered DDL schema string with only relevant tables
    """
    if full_schema is None:
        full_schema = get_schema_info_enhanced(plpy, include_examples=False)

    table_names = re.findall(r"CREATE TABLE (\w+)\s*\(", full_schema)
    if not table_names:
        return full_schema

    if len(table_names) <= 3:
        return full_schema

    table_list = ", ".join(table_names)
    selection_prompt = (
        f"Given the following database tables: {table_list}\n\n"
        f"User question: {question}\n\n"
        f"Which tables are needed to answer this question? "
        f"Return ONLY a JSON array of table names, nothing else. "
        f"Example: [\"orders\", \"customers\"]"
    )

    if call_model_fn is None:
        return full_schema

    try:
        response = call_model_fn(model_name, selection_prompt)
        response = response.strip()

        if "```json" in response:
            match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                response = match.group(1).strip()
        elif "```" in response:
            match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                response = match.group(1).strip()

        selected_tables = json.loads(response)
        if not isinstance(selected_tables, list):
            return full_schema

        selected_tables = [t.strip() for t in selected_tables if isinstance(t, str)]
    except (json.JSONDecodeError, Exception):
        return full_schema

    if not selected_tables:
        return full_schema

    filtered_parts = []
    current_table_ddl = []
    current_table_name = None
    in_create = False

    for line in full_schema.split("\n"):
        create_match = re.match(r"CREATE TABLE (\w+)\s*\(", line)
        if create_match:
            if current_table_ddl and current_table_name in selected_tables:
                filtered_parts.extend(current_table_ddl)
            current_table_name = create_match.group(1)
            current_table_ddl = [line]
            in_create = True
        elif in_create:
            current_table_ddl.append(line)
            if line.strip().startswith(");"):
                in_create = False
                if current_table_name in selected_tables:
                    filtered_parts.extend(current_table_ddl)
                current_table_ddl = []
                current_table_name = None
        elif current_table_name is None or current_table_name in selected_tables:
            if not in_create:
                if line.startswith("-- Example values"):
                    filtered_parts.append(line)
                elif line.startswith("  ") and current_table_name in selected_tables:
                    filtered_parts.append(line)
                elif not line.startswith("-- Example") and not line.startswith("  "):
                    pass

    result = "\n".join(filtered_parts)
    if not result.strip():
        return full_schema
    return result


def get_schema_info_basic(plpy) -> str:
    """Get basic schema info (backward compatible with old get_schema_info).

    Args:
        plpy: PostgreSQL PL/Python execution context

    Returns:
        Plain text schema description
    """
    query = """
    SELECT
        t.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable
    FROM information_schema.tables t
    JOIN information_schema.columns c ON t.table_name = c.table_name
    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
    ORDER BY t.table_name, c.ordinal_position;
    """
    try:
        result = plpy.execute(query)
        tables = {}
        for row in result:
            table_name = row["table_name"]
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append({
                "column": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"],
            })

        output = []
        for table_name, columns in tables.items():
            output.append(f"表: {table_name}")
            for col in columns:
                nullable = "NULL" if col["nullable"] == "YES" else "NOT NULL"
                output.append(f"  - {col['column']} ({col['type']}) {nullable}")
            output.append("")

        return "\n".join(output)
    except Exception as e:
        return f"无法获取schema信息: {e}"
