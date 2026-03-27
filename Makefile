# Makefile for pg_semantic_operators

# PostgreSQL 版本
PGVERSION = 16
PGSHARE = $(shell pg_config --sharedir)
PGINCLUDE = $(shell pg_config --includedir-server)

# 安装路径
EXTENSION = pg_semantic_operators
DATA = sql/$(EXTENSION).sql

# Python 模块路径
PYTHON_SITEPACKAGES = $(shell python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "/usr/lib/python3/dist-packages")

.PHONY: install install-python clean

# 安装扩展
install:
	@echo "安装 pg_semantic_operators 扩展..."
	@mkdir -p $(PGSHARE)/extension
	@mkdir -p $(PGSHARE)/lib
	cp $(DATA) $(PGSHARE)/extension/
	@echo "扩展已安装到 $(PGSHARE)/extension/"
	@echo ""
	@echo "请执行以下命令启用扩展:"
	@echo "  psql -d your_database -c 'CREATE EXTENSION plpython3u;'"
	@echo "  psql -d your_database -f $(PGSHARE)/extension/pg_semantic_operators.sql"

# 安装 Python 模块
install-python:
	@echo "安装 Python 依赖..."
	@pip install openai anthropic requests --quiet
	@echo "Python 依赖已安装"

# 完全安装 (扩展 + Python 依赖)
all: install-python install

# 清理
clean:
	rm -f $(PGSHARE)/extension/$(EXTENSION).sql

# 测试
test:
	@echo "运行测试..."
	@psql -d test -f sql/$(EXTENSION).sql

# 卸载
uninstall:
	rm -f $(PGSHARE)/extension/$(EXTENSION).sql
	@echo "已卸载扩展"