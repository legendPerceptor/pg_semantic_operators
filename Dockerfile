FROM postgres:18

RUN if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
      sed -i 's|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list; \
    elif [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources && \
      sed -i 's|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    else \
      echo "No known APT source file found" && exit 1; \
    fi && \
    apt-get update

RUN apt-get update && apt-get install -y \
    postgresql-plpython3-16 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy project and install Python package
WORKDIR /app
COPY pyproject.toml .env* ./
RUN pip install --break-system-packages -e .

# Copy SQL extension files
COPY sql/pg_semantic_operators--1.0.sql /docker-entrypoint-initdb.d/

# Install extension SQL into PostgreSQL's extension directory
RUN mkdir -p /usr/share/postgresql/16/extension/ && \
    cp /docker-entrypoint-initdb.d/pg_semantic_operators--1.0.sql /usr/share/postgresql/16/extension/ && \
    cp /docker-entrypoint-initdb.d/*.sql /usr/share/postgresql/16/extension/