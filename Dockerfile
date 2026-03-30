FROM postgres:18

ARG HTTP_PROXY
ARG HTTPS_PROXY

# Configure proxy for build (bypass for apt.postgresql.org)
ENV HTTP_PROXY=${HTTP_PROXY:-}
ENV HTTPS_PROXY=${HTTPS_PROXY:-}
ENV NO_PROXY=deb.debian.org,security.debian.org,mirrors.tuna.tsinghua.edu.cn,pypi.tuna.tsinghua.edu.cn

RUN if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
      sed -i 's|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list; \
    elif [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources && \
      sed -i 's|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    else \
      echo "No known APT source file found" && exit 1; \
    fi && \
    apt-get update

# Debian mirror already replaced above, now install packages
RUN apt-get update && apt-get install -y \
    postgresql-plpython3-18 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Copy project and install Python package
WORKDIR /app
COPY pyproject.toml README.md .env* ./
COPY pg_semantic_operators/ pg_semantic_operators/
RUN pip3 install --break-system-packages .

# Copy SQL extension file (runs on container first start)
COPY sql/pg_semantic_operators--1.0.sql /docker-entrypoint-initdb.d/

# Install extension files into PostgreSQL's extension directory
COPY pg_semantic_operators.control /usr/share/postgresql/18/extension/
RUN cp /docker-entrypoint-initdb.d/pg_semantic_operators--1.0.sql /usr/share/postgresql/18/extension/