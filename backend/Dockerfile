FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Layer 1 — install uv (rarely changes)
RUN pip install uv

# Layer 2 — dependency manifests (cached unless deps change)
COPY pyproject.toml uv.lock ./

# Layer 3 — install dependencies (cached unless pyproject/uv.lock change)
RUN uv sync --frozen

# Layer 4 — application code (changes most often, goes last)
COPY . .

EXPOSE 8000
EXPOSE 9000

CMD ["uv", "run", "python", "-m", "app.server"]
