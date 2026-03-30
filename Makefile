# Makefile for pg_semantic_operators
# Uses PostgreSQL Extension Building Infrastructure (PGXS)

EXTENSION = pg_semantic_operators
DATA = sql/pg_semantic_operators--1.0.sql

PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

.PHONY: install-python all test-models quick_test help

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

test-models:
	@echo "测试模型调用..."
	@python3 tests/test_models.py

quick_test:
	@echo "快速测试模型 (用法: make quick_test MODEL=gpt-4o)"
	@python3 tests/quick_test.py $(MODEL)

help:
	@echo "pg_semantic_operators - PostgreSQL 语义算子扩展"
	@echo ""
	@echo "可用命令:"
	@echo "  make install        - 安装SQL扩展到PostgreSQL (PGXS)"
	@echo "  make install-python - 使用uv安装Python依赖"
	@echo "  make all            - 完整安装（Python依赖 + SQL扩展）"
	@echo "  make test-models    - 测试模型调用"
	@echo "  make quick_test     - 快速测试单个模型 (用法: make quick_test MODEL=gpt-4o)"
	@echo "  make uninstall      - 卸载扩展"
	@echo "  make help          - 显示此帮助信息"
