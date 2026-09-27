FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY core ./core
COPY api ./api
COPY cli ./cli
COPY mcp_server ./mcp_server
COPY demo ./demo
RUN pip install --no-cache-dir -e .
ENV HEIRLOOM_HOME=/app/demo HEIRLOOM_DEMO=1
EXPOSE 8000
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
