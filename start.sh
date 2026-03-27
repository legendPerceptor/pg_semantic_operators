#!/bin/bash
set -e

echo "=== PostgreSQL 语义算子扩展 ==="
echo ""

if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入你的 API Key"
    exit 1
fi

echo "构建 Docker 镜像..."
docker compose build

echo ""
echo "启动 PostgreSQL 容器..."
docker compose up -d

echo ""
echo "等待数据库就绪..."
sleep 5

echo ""
echo "=== 数据库已启动 ==="
echo ""
echo "连接信息:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  User: postgres"
echo "  Password: postgres"
echo "  Database: semantic_test"
echo ""
echo "连接命令:"
echo "  docker exec -it pg_semantic psql -U postgres -d semantic_test"
echo ""
echo "或者使用本地 psql:"
echo "  psql -h localhost -U postgres -d semantic_test"
echo ""
echo "停止容器:"
echo "  docker compose down"
