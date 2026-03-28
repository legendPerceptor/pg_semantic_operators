# Makefile for pg_semantic_operators

PGSHARE = $(shell pg_config --sharedir 2>/dev/null || echo "/usr/share/postgresql/16")
EXTENSION = pg_semantic_operators
DATA = sql/$(EXTENSION).sql

.PHONY: install install-python all clean test test-models uninstall help

help:
	@echo "pg_semantic_operators - PostgreSQL 语义算子扩展"
	@echo ""
	@echo "可用命令:"
	@echo "  make install        - 安装SQL扩展到PostgreSQL"
	@echo "  make install-python - 使用uv安装Python依赖"
	@echo "  make all            - 完整安装（Python依赖 + SQL扩展）"
	@echo "  make test           - 运行SQL测试"
	@echo "  make test-models    - 测试模型调用"
	@echo "  make uninstall      - 卸载扩展"
	@echo ""
	@echo "使用示例:"
	@echo "  1. make all"
	@echo "  2. psql -d your_db -f $(PGSHARE)/extension/pg_semantic_operators.sql"

install:
	@echo "安装 pg_semantic_operators SQL扩展..."
	@mkdir -p $(PGSHARE)/extension
	cp $(DATA) $(PGSHARE)/extension/
	@echo "✓ 扩展已安装到 $(PGSHARE)/extension/"
	@echo ""
	@echo "在psql中执行以下命令启用扩展:"
	@echo "  \\i $(PGSHARE)/extension/pg_semantic_operators.sql"

install-python:
	@echo "安装 Python 依赖..."
	@if command -v uv >/dev/null 2>&1; then \
		uv pip install -e .; \
	else \
		pip install -e .; \
	fi
	@echo "✓ Python 依赖已安装"

all: install-python install
	@echo ""
	@echo "✓ 安装完成！"

clean:
	rm -f $(PGSHARE)/extension/$(EXTENSION).sql
	@echo "清理完成"

test:
	@echo "运行SQL测试..."
	@psql -d test -f sql/$(EXTENSION).sql

test-models:
	@echo "测试模型调用..."
	@python3 tests/test_models.py

test-quick:
	@echo "快速测试模型 (用法: make test-quick MODEL=gpt-4o)"
	@python3 tests/quick_test.py $(MODEL)

uninstall:
	rm -f $(PGSHARE)/extension/$(EXTENSION).sql
	@echo "✓ 已卸载扩展"
