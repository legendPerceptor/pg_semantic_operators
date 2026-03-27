FROM postgres:16

RUN apt-get update && apt-get install -y \
    postgresql-plpython3-16 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages \
    openai \
    anthropic \
    requests
